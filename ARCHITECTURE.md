# Architecture: Lab Sample Registry API

A small, production-style REST service used to teach API design. It stores DNA samples
(name, organism, sequence) and exposes CRUD over HTTP. Storage is in memory today; the
next module swaps it for SQLAlchemy 2.0 + Postgres without touching a single endpoint.

## 1. Tech stack

| Concern | Tool | Why |
|---|---|---|
| Web framework | FastAPI | Type hints drive routing, validation and OpenAPI docs (`/docs`) |
| Data contract | Pydantic v2 | Validation, normalization, computed fields, JSON serialization |
| ASGI server | Uvicorn | Runs the app: `uv run uvicorn app.main:app --reload` |
| HTTP client | httpx | Used by `client.py`, `fetch_uniprot.py` and FastAPI `TestClient` |
| Tests | pytest | In-process tests, no running server needed |
| Quality | ruff, mypy (strict + pydantic plugin) | Lint, format, static types |
| Packaging | uv (`pyproject.toml`, `uv.lock`) | Reproducible environment, one command setup |

Python 3.10+ is required, so the code avoids `datetime.UTC`, `enum.StrEnum` and `typing.Self`.

## 2. Layers

```mermaid
flowchart LR
    C[HTTP client] -->|JSON| R["routers/samples.py<br/>thin controllers"]
    R -->|validates with| S["schemas.py<br/>Pydantic DTOs"]
    R -->|Depends| D["dependencies.py<br/>DI wiring"]
    D --> P["repository.py<br/>SampleRepository Protocol"]
    P --> M[(InMemorySampleRepository<br/>dict of Sample)]
```

Each layer has one job and only talks to its neighbour:

| File | Responsibility | Must not |
|---|---|---|
| `app/schemas.py` | API contract: what clients may send and what they get back | know about storage or HTTP |
| `app/routers/samples.py` | Map HTTP (paths, status codes, headers) to repository calls | import storage code |
| `app/dependencies.py` | Build and hand out the repository; shared lookups such as 404 | contain business rules |
| `app/repository.py` | The only code that reads or writes storage | import FastAPI |
| `app/main.py` | Assemble the app from routers | hold endpoint logic |

Because routers depend on the `SampleRepository` Protocol, not on a concrete class, the
storage engine is a detail that can change behind the interface.

### Design patterns in the code

| Pattern | Where | What it buys |
|---|---|---|
| Application Factory | `create_app()` in `app/main.py` | Tests build a fresh app per test |
| DTO | `SampleCreate`, `SampleUpdate`, `SampleRead` | Clients cannot set server-owned fields |
| Repository | `SampleRepository` + `InMemorySampleRepository` | Storage swap without router changes |
| Dependency Injection | `RepoDep`, `SampleDep` via `Depends` | Routers receive what they need; tests override it |
| Singleton | `@lru_cache` on `get_repository()` | One shared store per process |
| Thin controller | each route is a few lines | HTTP concerns separate from data concerns |

## 3. Request lifecycle

Example: `POST /samples`.

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Router as create_sample
    participant DI as get_repository
    participant Repo as InMemorySampleRepository
    Client->>FastAPI: POST /samples {name, organism, sequence}
    FastAPI->>FastAPI: parse body into SampleCreate
    alt invalid body
        FastAPI-->>Client: 422 with error details
    end
    FastAPI->>DI: resolve RepoDep
    DI-->>Router: repository (singleton)
    Router->>Repo: add(payload)
    alt name already used
        Repo-->>Router: DuplicateNameError
        Router-->>Client: 409 Conflict
    end
    Repo-->>Router: Sample (id, created_at set)
    Router->>Router: SampleRead.model_validate(sample)
    Router-->>Client: 201 Created, Location: /samples/{id}
```

Steps worth noticing:

1. **Validation happens before your code runs.** If the body does not match `SampleCreate`,
   FastAPI returns 422 and the route function is never called.
2. **Dependencies are resolved per request.** `RepoDep` calls `get_repository()`, which is
   cached, so every request sees the same store.
3. **Domain errors become HTTP errors in the router.** The repository raises a plain
   `DuplicateNameError`; only the router knows that this means 409.
4. **Output goes through a response model.** `SampleRead.model_validate(sample)` reads the
   dataclass attributes (`from_attributes=True`) and adds computed fields.

For routes with `{sample_id}`, the `SampleDep` dependency (`get_sample_or_404`) parses the
UUID, loads the sample and raises 404 if it does not exist. The route body only ever sees a
real `Sample`.

## 4. Data models

There are two kinds of model, and keeping them apart is the main lesson of the module.

- **DTOs (Pydantic, `schemas.py`)**: the public contract over the wire.
- **Domain object (dataclass, `repository.py`)**: what storage holds. In the next module this
  becomes a SQLAlchemy model.

```mermaid
classDiagram
    class Organism {
        <<enum>>
        homo_sapiens
        mus_musculus
        escherichia_coli
    }
    class SampleBase {
        name: str (1..100)
        organism: Organism
        sequence: str (1..10000, ACGTN)
        validate_dna()
    }
    class SampleCreate
    class SampleUpdate {
        name: str | None
        organism: Organism | None
    }
    class SampleRead {
        id: UUID
        created_at: datetime
        length: int (computed)
        gc_content: float (computed)
    }
    class SampleResource {
        _links: dict of Link
    }
    class Link {
        href: str
        method: str = GET
    }
    class Page {
        items: list of SampleRead
        total: int
        limit: int
        offset: int
    }
    class Sample {
        <<dataclass>>
        name, organism, sequence
        id: UUID = uuid4()
        created_at: datetime = now(UTC)
    }
    SampleBase <|-- SampleCreate
    SampleBase <|-- SampleRead
    SampleRead <|-- SampleResource
    SampleResource --> Link
    Page --> SampleRead
    SampleRead ..> Sample : model_validate(from_attributes)
```

| Model | Used for | Key points |
|---|---|---|
| `Organism` | Allowed species | `str` Enum, so JSON values are plain strings; anything else is 422 |
| `SampleBase` | Shared fields | `validate_dna` runs before type checks: strips, uppercases, allows only `A C G T N` |
| `SampleCreate` | `POST` body | No `id` or `created_at`: the server owns them |
| `SampleUpdate` | `PATCH` body | Every field optional; `sequence` is deliberately not editable |
| `SampleRead` | Responses | Adds `id`, `created_at` and computed `length`, `gc_content` |
| `SampleResource` | `GET /samples/{id}` | Adds hypermedia links, serialized as `_links` |
| `Page` | `GET /samples` | Envelope with `items`, `total`, `limit`, `offset` |
| `Sample` | Storage | `slots=True` dataclass; default factories generate `id` and UTC `created_at` |

Why separate input and output models? If one model served both directions, a client could
send its own `id` or `created_at`, and derived values like `gc_content` would have to be
stored and kept in sync. Splitting them makes the contract explicit and safe.

Example: sending `"sequence": "atgcgc"` stores `ATGCGC` and returns `length: 6`,
`gc_content: 0.6667`.

## 5. REST API design

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/samples?organism=&limit=&offset=` | 200 `Page` | 422 |
| POST | `/samples` | 201 + `Location` header | 409, 422 |
| GET | `/samples/{id}` | 200 + `_links` | 404, 422 |
| PATCH | `/samples/{id}` | 200 | 404, 422 |
| DELETE | `/samples/{id}` | 204, empty body | 404 |
| GET | `/health` | 200 `{"status": "ok"}` | |

Design decisions:

- **Nouns in paths, verbs in methods.** One resource (`/samples`), one router.
- **Status codes carry meaning.** 201 plus `Location` tells the client where the new resource
  lives; 204 means success with nothing to return; 409 means the request conflicts with
  current state (duplicate name); 422 means the input is malformed.
- **Filtering and pagination via query parameters.** `limit` is 1..100 (default 20), `offset`
  is 0 or more. `total` lets clients compute the number of pages.
- **PATCH is a partial update.** The repository applies only fields the client actually sent
  (`model_dump(exclude_unset=True)`), so omitted fields are left untouched.
- **Richardson Maturity Level 3 (HATEOAS).** `GET /samples/{id}` returns `_links` with
  `self`, `update`, `delete` and `collection`. Clients follow links instead of building URLs.
  URLs are generated with `request.url_for`, so they stay correct if prefixes change.

## 6. Testing

`tests/test_samples.py` uses FastAPI `TestClient`, which calls the app in process: no server,
no network.

```python
app = create_app()
repo = InMemorySampleRepository()
app.dependency_overrides[get_repository] = lambda: repo
```

This is where Dependency Injection pays off: each test gets a brand new, empty repository,
so tests never share state. Coverage includes the happy path and every documented error:
201 + `Location`, 422 for bad sequence, organism and name, 409 on duplicates, the full CRUD
lifecycle, filtering + pagination, 404 on unknown id, and following a hypermedia link.

Conventions live in `tests/CLAUDE.md`. End-to-end tests with Robot Framework against a
running server are planned in `e2e/`.

## 7. Clients

- `client.py`: consumes this API with `httpx` exactly as another service would (create, list,
  rename, trigger a validation error, delete). Start the server first.
- `fetch_uniprot.py`: consumes a real public bio API (UniProt) and maps its JSON to a small
  `TypedDict`. Shows the consumer side: timeouts and `raise_for_status()`.
- HTTPie from the terminal: see [docs/httpie.md](docs/httpie.md) for testing every endpoint
  without Swagger UI.

## 8. Tooling and quality gate

`uv run python scripts/check.py` runs, stopping at the first failure:

1. **dashes**: no em or en dash characters in project text files (house style)
2. **pytest**
3. **ruff** lint
4. **mypy** strict on `app/`

The summary is short; full output goes to `.claude/logs/check.log`.

`.claude/settings.json` wires Claude Code hooks: `uv sync` on session start, a guard that
forces `uv run` instead of bare `pip`/`python`, auto format + lint and a dash check after
every edit, and a check run when a session stops.

## 9. Limitations and next steps

Limitations of the in-memory store (acceptable for a demo, not for production):

- Data is lost on restart and not shared between worker processes.
- No locking, so concurrent writes are not safe.
- The duplicate name check scans every item (O(n)); a database would use a unique index.

Exercises:

1. Add `GET /samples/{id}/reverse-complement`.
2. Implement `SampleRepository` with SQLAlchemy 2.0 + Postgres. Only `get_repository()` in
   `app/dependencies.py` should change; routers stay the same.
3. Add an `X-API-Key` header dependency that returns 401 when missing.

## 10. Run it

```bash
uv sync                               # create .venv and install everything
uv run uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
uv run python client.py               # in a second terminal
uv run pytest                         # tests, no server needed
uv run python scripts/check.py        # tests + lint + types
```
