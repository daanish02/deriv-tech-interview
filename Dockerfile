# syntax=docker/dockerfile:1.7
# ── enables RUN --mount=type=cache (BuildKit feature) ────────────────────────

# ============================================================================
# Stage 1: Builder — install uv, resolve dependencies, build the virtualenv
# ============================================================================
FROM python:3.12-slim AS builder

# PYTHONDONTWRITEBYTECODE: skip .pyc files — not needed in containers.
# PYTHONUNBUFFERED:        flush stdout/stderr immediately so logs appear in docker logs.
# UV_COMPILE_BYTECODE:     pre-compile .py → .pyc during install for faster cold starts.
# UV_LINK_MODE=copy:       copy files into the venv instead of hard-linking
#                          (required when builder and runtime share different inodes).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Pull uv binary from the official image — avoids a pip install of uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests before source code so Docker can cache the
# dependency install layer independently of application code changes.
COPY pyproject.toml uv.lock ./

# Install all dependencies into /app/.venv.
# --frozen:             use exact versions from uv.lock, never re-resolve.
# --no-install-project: skip installing the project itself (done in next step).
# --no-dev:             exclude dev/test dependencies from the runtime image.
# RUN --mount=type=cache caches the uv download cache across builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy all application source after deps are installed to maximise cache hits.
COPY config.py main.py validate.py api_main.py ./
COPY pipeline/ ./pipeline/
COPY models/ ./models/
COPY api/ ./api/

# Install the project package itself (registers console scripts from pyproject.toml).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================================
# Stage 2: Runtime — minimal image containing only what is needed to run
# ============================================================================
FROM python:3.12-slim AS runtime

# Create a non-root user so the container process cannot write to system paths.
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Prepend the virtualenv to PATH so python/uvicorn/run-pipeline resolve without
# activating the venv explicitly.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    LOG_LEVEL=INFO

WORKDIR /app

# Copy only the pre-built virtualenv from the builder — no build tools in runtime.
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application source with correct ownership for the non-root user.
COPY --chown=appuser:appgroup config.py main.py validate.py api_main.py ./
COPY --chown=appuser:appgroup pipeline/ ./pipeline/
COPY --chown=appuser:appgroup models/ ./models/
COPY --chown=appuser:appgroup api/ ./api/

# Copy static input data files that the pipeline reads at runtime.
COPY --chown=appuser:appgroup incident_a.log incident_b.log historical_incidents.json ./

# Pre-create the output directory so the pipeline can write without root privileges.
RUN mkdir -p parsed_logs && chown appuser:appgroup parsed_logs

USER appuser

# Declare the port exposed by the API server (documentation; does not publish it).
# Pass -p 8000:8000 to docker run to make it reachable from the host.
EXPOSE 8000

# Health check adapts to the active run mode:
#   RUN_MODE=api  → HTTP GET /api/health (server must be running)
#   default       → Python import check (pipeline mode, no server)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
        "import os, urllib.request; \
         urllib.request.urlopen('http://localhost:8000/api/health') \
         if os.environ.get('RUN_MODE') == 'api' \
         else __import__('config')" \
    || exit 1

# Default command: run the one-shot analysis pipeline and exit.
CMD ["python", "main.py"]

# ─── Alternative run modes ───────────────────────────────────────────────────
# API server (long-running, exposes port 8000):
#   docker run -e RUN_MODE=api -p 8000:8000 --env-file .env <image> python api_main.py
#
# Validate pipeline outputs:
#   docker run --env-file .env <image> python validate.py
#
# Interactive shell for debugging:
#   docker run --env-file .env -it <image> /bin/bash
