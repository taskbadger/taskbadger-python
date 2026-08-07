# Task Badger Python SDK

Official Python client for [Task Badger](https://taskbadger.net/). Public package: `taskbadger` on PyPI.

## Commands

```bash
uv sync --frozen          # Install deps (incl. dev + cli extras via dependency-groups)
uv run pytest             # Run unit tests (needs Redis; integration_tests/ excluded by default)
uv run pytest integration_tests -vs   # Run integration tests (needs Redis + Postgres + API key)
uv run ruff check . --fix # Lint
uv run ruff format .      # Format
uv build                  # Build sdist + wheel
```

Pre-commit runs ruff-check + ruff-format; install with `uv run pre-commit install`.

## Architecture

- `taskbadger/` — SDK source
  - `sdk.py`, `mug.py`, `safe_sdk.py` — public API surface (re-exported from `__init__.py`)
  - `decorators.py` — `@track` decorator
  - `celery.py`, `procrastinate.py` — per-queue integrations (optional extras)
  - `systems/`, `_integrations.py` — auto-tracking layer (`BaseSystemIntegration`) wired onto a Celery/Procrastinate app
  - `context_providers/`, `_error_context.py` — pluggable error context (e.g. Sentry issue links) via `init(context_providers=[...])`
  - `_heartbeat.py` — background thread pinging long-running tasks
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
- Extras (`celery`, `procrastinate`, `cli`, `sentry`) are all optional; keep their imports inside the corresponding module (`taskbadger/celery.py`, `taskbadger/procrastinate.py`, `taskbadger/systems/`, `taskbadger/cli/`, `taskbadger/context_providers/sentry.py`).
- `taskbadger/internal/*` is generator output — lint is best-effort, don't reformat manually.

## Releasing

```bash
uv run invoke tag-release  # Bumps version in pyproject.toml, tags, pushes — triggers release.yml
```

GitHub Actions then drafts a release; publishing the release triggers `publish.yml` → PyPI.

## Gotchas

- `pytest` skips `integration_tests/` via `norecursedirs` — name them explicitly to run.
- Integration tests need `TASKBADGER_ORG`, `TASKBADGER_PROJECT`, `TASKBADGER_API_KEY`, a running Redis, and Postgres via `PROCRASTINATE_DSN` (defaults to `postgresql://postgres:postgres@localhost:5432/procrastinate`).
- Unit tests also need Redis — `tests/conftest.py` points Celery at `redis://localhost:6379` so serialization is exercised for real.
- Don't unpin `openapi-python-client<0.29` — 0.29 generates `datetime.fromisoformat` calls that can't parse the API's `Z`-suffixed timestamps on Python 3.10.
- User-facing features are documented in `README.md`, not a docs site — add a section there when adding one.
- Only the core httpx/attrs/dateutil/tomlkit deps are guaranteed at runtime.
