# syntax=docker/dockerfile:1

# Dependencies are installed at build time, not on every container start.
# The original setup ran `pip install` in the compose command, which made
# every boot slow and every start dependent on the network being up.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copied on its own so the layer caches until the dependencies actually change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Runs unprivileged. The data directory is created and handed over before the
# user is dropped, so the volume mount stays writable.
RUN useradd --create-home --uid 10001 mimic \
    && mkdir -p /app/data \
    && chown -R mimic:mimic /app
USER mimic

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]


# --- Development ------------------------------------------------------------
# Adds the test tooling and enables autoreload. Selected with
# `target: dev` in docker-compose.
FROM base AS dev

USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
USER mimic

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
