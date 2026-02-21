# Repository Guidelines

## Project Structure & Module Organization
- Root orchestrates a multi-service TRPG platform.
- `services/` contains git submodules: `BE-router`, `gm`, `state-manager`, `scenario-service`, `rule-engine`, `llm-gateway`, `WEB`.
- `tester/src/tester/` contains integration runner and test agent code.
- `db/` holds Postgres compose, init SQL, and migration helpers.
- `docs/dev/` tracks architecture, plans, and detailed execution docs.
- `bin/project` is the primary local orchestration wrapper.

## Build, Test, and Development Commands
- `./bin/project up` : start the full local stack with `docker-compose.local.yml`.
- `./bin/project ps` : show running containers and ports.
- `./bin/project logs gm` : tail logs for a specific service.
- `./bin/project down` : stop and remove local containers.
- `docker compose -f docker-compose.local.yml -p gtrpg-local config --services` : validate compose/service wiring.
- Service-level tests (run inside each service directory): `uv run pytest tests/`.
- Integration runner from repo root: `PYTHONPATH=tester/src uv run python -m tester.runner <session_id> <max_turns>`.
- Quality checks: `uv run pre-commit run -a`.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, max line length 88.
- Formatting/linting uses Ruff (`ruff`, `ruff-format`) via pre-commit.
- Prefer explicit, typed interfaces for cross-service contracts.
- Follow existing package layouts (`src/<package>`, `tests/`).
- Plan docs use `docs/dev/detail/plan_0001.md` naming.

## Testing Guidelines
- Framework: `pytest` (+ `pytest-asyncio`, `pytest-cov` in services).
- Place tests under each service’s `tests/` directory.
- Name files `test_*.py`; keep API/contract tests near integration boundaries.
- For schema/path changes, include at least one proof step: unit or integration execution output.

## Commit & Pull Request Guidelines
- Use concise prefix style seen in history: `feat:`, `fix:`, `chore:`, `ops:`.
- Keep commits scoped to one logical change (e.g., schema alignment, path migration).
- PRs should follow `.github/pull_request_template.md`: linked issue, change summary, rationale, implementation notes, and checklist.
- Include docs updates when behavior, contracts, or structure changes.

## Security & Configuration Tips
- Keep secrets in local env files (`.env.*`); never commit API keys.
- LLM-dependent flows may fail without `OPENAI_API_KEY` or `GOOGLE_API_KEY`.
