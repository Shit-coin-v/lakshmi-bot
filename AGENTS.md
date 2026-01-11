# Agent Instructions for `lakshmi-bot`

## Scope
- Repo: `lakshmi-bot`.
- Do **not** change business logic, model semantics, or API contracts.
- Structural refactors only: file/directory moves, path updates, infra config tweaks, and documentation clarifications.

## .env Handling
- The secret `.env` is not stored in git; do not expect it to exist in the repo.
- Keep only `*.env.example` files in version control.
- For local runs, users create `.env` from `.env.example`; never commit the resulting `.env`.

## Target Structure
- Final layout removes `backend_bot/`.
- Backend lives in `/backend/`.
- Docker Compose file resides at `/infra/docker/docker-compose.yml`.

## Docker Compose Rules
- In `infra/docker/docker-compose.yml`, use `env_file: ../../backend/.env` as the final path.
- Do **not** use long-form `env_file` syntax with `path`/`required` keys.
- If `.env` is missing locally, the correct flow is copying from `backend/.env.example` to `backend/.env` (the `.env` remains untracked).

## Path Guidance
- All paths should be correct relative to `infra/docker/docker-compose.yml`.
- Update paths as directories move—do not guess future layouts without verifying the tree/plan.

## PR Workflow
- PRs are created via the GitHub Pull Request UI (web interface).
- Avoid instructions about manual `git push`/PR creation unless explicitly requested.

## Testing
- Do not claim Docker Compose validation was run if Docker is unavailable.
- If Docker is available, the minimal check is `docker compose -f infra/docker/docker-compose.yml config`.
