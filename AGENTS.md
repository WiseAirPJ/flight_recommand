# Repository conventions

- Name branches by work type: `feat/<topic>`, `refactor/<topic>`, `fix/<topic>`, or `chore/<topic>`. Do not use `codex/`.
- Run backend checks from `backend/` with Python 3.14 and uv 0.12.19. Use `uv sync --locked`, then `uv run --locked` for commands. Update dependencies in `pyproject.toml` and commit `uv.lock`; do not maintain requirements files. Follow the commands in README.md and `.github/workflows/backend-ci.yml`.
- Keep real provider observations separate from demo/test prices. Never label a sampled minimum as an exhaustive monthly minimum.
