# syntax=docker/dockerfile:1
# Lab Sample Registry API: production image (multi-stage, uv, non-root).
# Build from the repo root:  docker build -t lab-sample-registry .

# ---------- builder: resolve and install dependencies from uv.lock ----------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Dependencies first: this layer is rebuilt only when pyproject.toml or uv.lock change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Application code: changes often, so it comes last.
COPY . /app
# chmod: readable by any UID, whatever the host umask (Apptainer runs the image as the caller).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked \
    && chmod -R a+rX /app

# ---------- runtime: no uv, no build tools, non-root ----------
FROM python:3.12-slim AS runtime
# Fixed numeric UID/GID: lets ECS/Kubernetes verify "runAsNonRoot" without /etc/passwd.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app
WORKDIR /app
COPY --from=builder --chown=10001:10001 /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", \
         "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
# --proxy-headers: trusts X-Forwarded-* so _links use https when a reverse proxy/load balancer
# sits in front (this demo's bare EC2 host has none; a real deployment would add one and scope
# --forwarded-allow-ips to it instead of "*").
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
