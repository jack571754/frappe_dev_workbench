# Repository Guidelines

## Project Structure & Module Organization
This repository packages and orchestrates Frappe with Docker.

- `compose.yaml`: base production compose definition.
- `pwd.yml`: disposable demo stack for quick local trials.
- `overrides/`: scenario-specific compose overrides (MariaDB, TLS, proxy, multi-bench, etc.).
- `images/`: Docker build definitions (`bench/`, `production/`, `custom/`, `layered/`).
- `development/` and `devcontainer-example/`: local development and editor container setup.
- `tests/`: pytest-based integration checks (for compose, connectivity, and site behavior).
- `docs/`: canonical project documentation.

## Build, Test, and Development Commands
- `docker compose -f pwd.yml up -d`: start disposable demo environment.
- `docker compose -f compose.yaml -f overrides/compose.mariadb.yaml config`: validate merged compose config.
- `FRAPPE_VERSION=... ERPNEXT_VERSION=... docker buildx bake <target>`: build images via bake (`docker-bake.hcl` defines targets).
- `python -m venv venv && .\\venv\\Scripts\\Activate.ps1` (Windows) or `source venv/bin/activate` (Linux/macOS): create/activate test env.
- `pip install -r requirements-test.txt && pytest`: install test deps and run integration tests.
- `pre-commit install && pre-commit run --all-files`: run formatting/lint hooks before PR.

## Coding Style & Naming Conventions
- Follow `.editorconfig`: UTF-8, LF endings, final newline; default indent `2` spaces, Python indent `4`.
- Pre-commit enforces style with `black`, `isort`, `prettier`, `shellcheck`, `shfmt`, and `codespell`.
- Keep file/folder names descriptive and aligned with existing patterns (for example `compose.<feature>.yaml` in `overrides/`).

## Testing Guidelines
- Framework: `pytest` (configured in `setup.cfg` with `-s --exitfirst`).
- Add tests under `tests/` using `test_*.py` naming.
- Prefer integration-oriented assertions for container health, service connectivity, and compose behavior.
- Run `pytest` locally before opening a PR.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `<type>(<scope>): <description>` when scope is helpful.
- Common types in this repo: `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`.
- Example: `fix(proxy): add acme label for nginx-proxy`.
- PRs should include: purpose, related issue(s), documentation updates (if behavior changed), and passing pre-commit/test results.
- Test image/build changes locally before submitting.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
