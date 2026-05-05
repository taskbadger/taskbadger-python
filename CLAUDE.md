# Task Badger Python SDK

Official Python client for [Task Badger](https://taskbadger.net/). Public package: `taskbadger` on PyPI.

## Commands

```bash
uv sync --frozen          # Install deps (incl. dev + cli extras via dependency-groups)
uv run pytest             # Run unit tests (integration_tests/ is excluded by default)
uv run pytest integration_tests -vs   # Run integration tests (needs Redis + TASKBADGER_API_KEY)
uv run ruff check . --fix # Lint
uv run ruff format .      # Format
uv build                  # Build sdist + wheel
```

Pre-commit runs ruff-check + ruff-format; install with `uv run pre-commit install`.

## Architecture

- `taskbadger/` — SDK source
  - `sdk.py`, `mug.py`, `safe_sdk.py` — public API surface (re-exported from `__init__.py`)
  - `decorators.py` — `@track` decorator
  - `systems/`, `celery.py` — Celery integration (optional extra)
  - `cli/`, `cli_main.py` — Typer-based CLI (optional `[cli]` extra)
  - `internal/` — **generated** by `openapi-python-client`; do not hand-edit
- `tests/` — unit tests (pytest, pytest-httpx)
- `integration_tests/` — hits real Task Badger API; excluded from default pytest run
- `taskbadger.yaml` — OpenAPI schema used to regenerate `internal/`

## Regenerating the API client

```bash
uv run invoke update-api          # Pull latest schema + regenerate
uv run invoke update-api --local  # Regenerate from existing taskbadger.yaml
```

The `update-api` invoke task curls `localhost:8000/api/schema.json` by default — pass `--local` if you don't have the API server running.

## Code Style

- Ruff: line-length 120, target Python 3.10, rules `E F I UP DJ PT`.
- Supports Python 3.10–3.14 — don't use 3.11+ syntax (e.g. `Self`, `LiteralString`).
- Celery and CLI deps are optional; guard imports inside `taskbadger/celery.py`, `taskbadger/systems/celery.py`, `taskbadger/cli/`.
- `taskbadger/internal/*` is generator output — lint is best-effort, don't reformat manually.

## Releasing

```bash
uv run invoke tag-release  # Bumps version in pyproject.toml, tags, pushes — triggers release.yml
```

GitHub Actions then drafts a release; publishing the release triggers `publish.yml` → PyPI.

## Gotchas

- `pytest` skips `integration_tests/` via `norecursedirs` — name them explicitly to run.
- Integration tests need `TASKBADGER_ORG`, `TASKBADGER_PROJECT`, `TASKBADGER_API_KEY` env vars and a running Redis.
- Imports of `celery`, `typer`, `rich` must stay optional — only the core httpx/attrs deps are guaranteed.
