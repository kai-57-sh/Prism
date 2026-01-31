# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service, core logic in `backend/src/`, tests in `backend/tests/`.
- `frontend/`: Gradio UI in `frontend/src/` with its own `requirements.txt`.
- `docker/`: Nginx and Docker Compose setup for multi-container runs.
- `scripts/`: Local setup, deploy, and test helpers.
- `docs/` and `specs/`: Reference material and feature plans.
- Runtime outputs live in `./static/` and `/var/lib/prism/static` (videos/audio/metadata).

## Build, Test, and Development Commands
- `./scripts/setup.sh` creates a Python 3.11 venv, installs backend/frontend deps, and creates static dirs (may need permissions for `/var/lib/prism`).
- `cd backend && ./run_dev.sh` loads `backend/.env` and runs FastAPI on `:8000`.
- `cd frontend && ./run_dev.sh` starts Gradio on `:7860` (set `BACKEND_URL` if needed).
- `./scripts/deploy.sh` runs Docker Compose build/up; `./scripts/stop.sh` stops services.
- `ruff check .`, `black .`, `mypy backend/src` for linting, formatting, and type checks.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, 100-char line length (ruff/black).
- Type hints are required; mypy runs with strict settings.
- Use `snake_case` for modules/functions, `PascalCase` for classes, `test_*.py` for tests.
- Keep API routes in `backend/src/api` and shared services in `backend/src/services`.

## Testing Guidelines
- Tests are organized under `backend/tests/{unit,integration,contract}`.
- Run all tests with `./scripts/test.sh` (activates venv and runs pytest).
- Targeted runs: `cd backend && pytest tests/unit/ -v` (similar for integration/contract).
- Integration tests may require API keys, Redis, and network access; expect skips if env is missing.
- Optional coverage: `pytest tests/ --cov=src --cov-report=html`.

## Commit & Pull Request Guidelines
- Git history shows short, sentence-case subjects without scopes or ticket IDs; keep commits brief and descriptive.
- PRs should include a summary, testing notes (commands + results), and config/env changes; add UI screenshots when frontend behavior changes.

## Configuration & Secrets
- Copy `.env.example` to `.env` (and/or `backend/.env`) and fill required API keys.
- Frontend overrides live in `frontend/.env` (see `frontend/.env.example`).
- Never commit secrets; Docker Compose reads env vars from your shell or a local `docker/.env`.
