# Notes CLI instructions

## Scope

This directory contains the Python command-line client for the Notes application.

## Architecture

- `cli.py` defines commands and presentation.
- Supabase operations belong in client/service modules.
- Configuration and session persistence belong in dedicated modules.
- Command functions should remain small.
- The database schema is owned by the repository-level `supabase/` directory.

## Security

- Use only `SUPABASE_PUBLISHABLE_KEY`.
- Never use or expose `SUPABASE_SECRET_KEY` or `SERVICE_ROLE_KEY`.
- Do not send `user_id` when creating owned records.
- Let PostgreSQL and RLS determine ownership through `auth.uid()`.
- Store sessions outside the repository with restrictive permissions.
- Never print access or refresh tokens.

## Dependencies

- Manage dependencies with uv.
- Commit `pyproject.toml` and `uv.lock`.
- Do not install dependencies with raw `pip`.
- Do not create a shared package until another real application needs it.

## Validation

Run before completing changes:

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run notes --help
```
