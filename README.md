# Lab Sample Registry API: REST demo

Minimal, production-style FastAPI service for the Module 02 REST API session.
See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works.

## Run

Two ways to run this locally; pick one.

### Option A: Docker only (no Python/uv needed)

```bash
docker compose --profile prod up --build   # db healthy -> migrate exits 0 -> api on :8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs), or `curl localhost:8000/health`.
Add `--watch` to get hot reload without rebuilding (see [Containers](#containers)). Stop with:

```bash
docker compose --profile prod down         # add -v to also drop the dev database volume
```

See [Containers](#containers) below for what each step does, a non-root uid check, and more.

### Option B: local with uv (Python 3.10+; for active development: hot reload, debugger)

```bash
cp .env.example .env                  # DATABASE_URL / TEST_DATABASE_URL
docker compose up -d db               # dev Postgres (test_db starts itself for pytest)
uv sync                               # creates .venv, installs app + ruff + mypy + pytest
uv run alembic upgrade head           # create the schema
uv run uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
uv run python client.py               # in a 2nd terminal
uv run pytest                         # auto-starts test_db, rolled back per test
uv run python scripts/check.py        # tests + lint + types, compact output
uv tool install httpie                # CLI testing, see docs/httpie.md
```

#### Windows

The commands above are bash (WSL, Git Bash, macOS/Linux). Two ways to run on Windows:

- **WSL (recommended)**: open a WSL terminal in the project directory and run the commands above
  unchanged. Docker Desktop must have WSL2 integration enabled for `docker compose` to reach it.
- **Native PowerShell**: same commands, except copy the env file with
  `Copy-Item .env.example .env` instead of `cp`. `uv`, `docker compose`, `uv run ...` work the
  same in PowerShell as in bash.

## Local database access

The dev Postgres instance (`db`) is for manual poking around: running ad hoc queries, checking
what a request actually wrote, inspecting the schema. It's separate from `test_db`, which tests
own exclusively and which is never meant to be queried by hand.

```bash
docker compose up -d db                         # make sure it's running
docker compose exec db psql -U app -d lab_samples   # opens a psql shell inside the container
```

Inside `psql`: `\dt` lists tables, `\d samples` describes the `samples` table, `select * from
samples;` shows what's there. `\q` exits.

To connect with a host-side client instead (DBeaver, TablePlus, VS Code extensions, a native
`psql`), use the connection details from `.env`'s `DATABASE_URL`: host `localhost`, port `5434`
(see `docker-compose.yml`'s `db` port mapping), user/password `app`, database `lab_samples`.

## Housekeeping

```bash
docker compose down                   # stop db + test_db, keep dev data (named volume)
docker compose down -v                # also delete the dev volume: next `up` starts from empty
docker compose --profile prod down    # stop the full app stack (db, migrate, api)
docker compose logs -f db             # tail the dev Postgres container's logs
uv run alembic downgrade -1           # revert the last migration (dev db)
uv run alembic upgrade head           # re-apply migrations (dev db)
rm -rf .ruff_cache .mypy_cache .pytest_cache  # clear tool caches if they ever get confused
```

`test_db` has no named volume, so it always starts empty; there's nothing to reset there besides
restarting the container.

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /api/v1/samples?organism=&limit=&offset= | 200 | 422 |
| POST | /api/v1/samples | 201 + Location | 409, 422 |
| GET | /api/v1/samples/{id} | 200 + `_links` (Richardson L3) | 404, 422 |
| PATCH | /api/v1/samples/{id} | 200 | 404, 422 |
| DELETE | /api/v1/samples/{id} | 204 | 404 |
| GET | / | 200, HTML page: samples table + Add/Edit/Delete sidebar | - |
| GET | /health | 200 | - |

## Layout & patterns

```
app/
  main.py           # Application Factory (create_app), wires the db lifespan
  config.py         # Settings (pydantic-settings), env-driven DATABASE_URL
  db.py             # async engine/session lifecycle (lifespan + per-request session)
  models.py         # SQLAlchemy 2.0 declarative models (table shape only)
  schemas.py        # DTOs: Pydantic contract, validation, computed fields
  repository.py     # Repository pattern (Protocol + in-memory + SQLAlchemy impls)
  dependencies.py   # Dependency Injection via Depends
  routers/samples.py# thin async controllers, one router per resource
  api/router.py     # /api/v1 aggregator: mounts resource routers under the version prefix
  frontend/         # HTML frontend: router + templates + static, separate from the JSON API
                     # so it can be swapped for a SPA later without touching anything above.
                     # static/js/app.js adds/edits/deletes samples by calling the same /api/v1
                     # endpoints from the browser, then re-renders the table.
alembic/            # schema migrations (async env.py, autogenerate from Base.metadata)
tests/              # pytest-asyncio + httpx AsyncClient + dependency_overrides
docker-compose.yml  # dev (db) + test (test_db) Postgres; "prod" profile: migrate + api
client.py           # httpx consumer
Dockerfile          # multi-stage image (uv builder, non-root slim runtime), see "Containers"
.dockerignore       # keeps .env, .venv, tests, tooling out of the image
deploy/             # ec2-bootstrap.sh (EC2 user data), deploy.sh (SSM Run Command deploy)
infra/              # Terraform: EC2 demo host, ECR, GitHub OIDC deploy role (+ tests/)
apptainer/          # Apptainer (Singularity) definition for HPC clusters
.github/workflows/  # ci-cd.yml: checks on every PR; build -> ECR -> deploy to EC2 on main
```

## Containers

```bash
docker compose --profile prod up --build   # db healthy -> migrate exits 0 -> api on :8000
curl localhost:8000/health                 # {"status":"ok"}
curl -s localhost:8000/api/v1/samples -H "X-Forwarded-Proto: https"   # _links use https
docker compose exec api id                 # uid=10001(app): not root
docker compose --profile prod down         # add -v to also drop the dev database volume
```

The `prod` services are exactly what runs on the EC2 host; config comes only from the environment.
Without `--profile prod`, `docker compose` behaves as before (`db`, `test_db` only).
The image runs on port 8000 like `uvicorn --reload`, so stop the dev server first.

### Hot reload under Docker (Compose Watch)

Add `--watch` to the same command to edit `app/` on the host and see it live in the
container, with no `uv` and no rebuild:

```bash
docker compose --profile prod up --build --watch
```

`docker-compose.yml`'s `api` service declares a `develop.watch` block: changes under
`app/` are synced straight into the running container and the process restarts
(`sync+restart`); changes to `pyproject.toml`/`uv.lock` trigger a real `rebuild`
instead, since a file sync can't add a new dependency. `watch` only runs when you ask
for it (`--watch` or `docker compose watch`); a plain `up`/`up -d` - what
`deploy/deploy.sh` runs on EC2 - ignores the `develop:` key entirely, so this has no
effect on the deployed stack.

## HPC: Apptainer / Singularity

Clusters rarely allow Docker (root daemon). Apptainer (formerly Singularity) runs the same image
as a single read-only `.sif` file, as your own user, without a daemon:

```bash
docker compose --profile prod build api                                     # Docker image first
apptainer build lab-sample-registry.sif apptainer/lab-sample-registry.def   # Linux/WSL
apptainer test lab-sample-registry.sif                                      # import check
export DATABASE_URL=postgresql+asyncpg://user:pass@dbhost:5432/lab_samples
apptainer exec --pwd /app lab-sample-registry.sif alembic upgrade head
PORT=8000 apptainer run lab-sample-registry.sif                             # uvicorn on 127.0.0.1
```

## Deploy to AWS: minimal EC2 demo

One t3.small instance (Amazon Linux 2023) runs the same `docker compose --profile prod` stack;
images come from ECR. No SSH: access and deploys go through SSM. No load balancer, NAT or RDS.

```
GitHub Actions --OIDC--> AWS --push--> ECR <--pull-- EC2 host (docker compose: db, migrate, api)
               --SSM Run Command (deploy/deploy.sh)---^            ^-- clients: http://<host>/docs
```

1. Create the infrastructure once (`infra/`, Terraform >= 1.11 or OpenTofu):

   ```bash
   cd infra
   cp terraform.tfvars.example terraform.tfvars   # set github_repo = "<owner>/<repo>"
   terraform init                                 # downloads the AWS provider, writes .terraform.lock.hcl (commit it)
   terraform test                                 # offline checks with a mocked AWS provider
   terraform plan -out tfplan                     # review: ~17 resources to add
   terraform apply tfplan
   ```

   Creates: VPC with one public subnet, security group (port 80 only), instance with IAM role
   (SSM + pull from this ECR repository only), encrypted 20 GB gp3 disk, IMDSv2 with hop limit 1
   (containers cannot read the instance role), ECR repository `lab-sample-registry` (immutable
   tags, scan on push), GitHub OIDC provider and deploy role. On first boot
   `deploy/ec2-bootstrap.sh` installs Docker + Compose and writes `/opt/lab-samples/.env`
   with a generated `POSTGRES_PASSWORD` (never in git or the image).
   Account already has the GitHub OIDC provider? Set `create_github_oidc_provider = false`.
   State is local (`terraform.tfstate`, git-ignored); for a team, enable the S3 backend in
   `versions.tf` (native locking with `use_lockfile = true`).

2. GitHub repository variables (from `terraform output`): `AWS_DEPLOY_ROLE_ARN`,
   `EC2_INSTANCE_ID`. Create the environment `production`: the deploy role only trusts
   `repo:<owner>/<repo>:environment:production`. No AWS access keys are stored in GitHub.

3. Push to `main`. Pipeline (`.github/workflows/ci-cd.yml`):
   - `test` (every PR and push): `uv sync --locked`, `scripts/check.py`
   - `terraform` (every PR and push): `fmt -check`, `init -backend=false`, `validate`, `test`
   - `deploy`: OIDC login, build + push image tagged with the commit SHA, then
     `deploy/deploy.sh` via SSM: copy `docker-compose.yml`, set `IMAGE`, `compose pull`,
     `compose up` (migrate runs once and must exit 0 before api starts), poll `/health`.
     A failed migration or health check fails the job.

4. Open the `api_url` output (`http://<public-dns>/docs`). Shell on the host without SSH:
   `aws ssm start-session --target <instance-id>`, then
   `cd /opt/lab-samples && sudo docker compose --profile prod ps`.

5. After the course: `terraform destroy` (deletes the instance, its data and the images).

Demo trade-offs (production moves to ECS Fargate + ALB + RDS): one instance in one AZ,
a few seconds of downtime per deploy (containers are recreated), plain HTTP, the database
lives on the instance disk, and you patch the OS (`sudo dnf upgrade`). The public DNS name
changes if the instance is stopped and started.

## Exercises

1. Add `GET /api/v1/samples/{id}/reverse-complement`.
2. Add an `X-API-Key` header dependency that returns 401 when missing.
3. Add a second Alembic revision (e.g. an index, or a new column) and confirm `alembic upgrade
   head` / `alembic downgrade -1` both work cleanly.
