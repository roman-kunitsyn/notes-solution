# Notes CLI instructions

Follow the repository-wide [workflow and completion requirements](../../AGENTS.md).
The [CLI roadmap](ROADMAP.md) owns planned client behavior; do not document it
as current behavior.

## Architecture

- `src/notes_cli/cli.py` defines commands and presentation only; keep command
  functions small.
- Put Supabase operations in the client, Notes, and attachment modules.
- Keep configuration and session persistence in their dedicated modules.
- The repository-level `supabase/` directory owns the database schema.
- Do not create a shared package until another application has a real need for
  one.

## Security

- Use only `SUPABASE_PUBLISHABLE_KEY`; never use or expose secret or
  service-role keys.
- Do not send `user_id` for owned records; PostgreSQL and RLS establish
  ownership through `auth.uid()`.
- Keep sessions outside the repository with restrictive permissions, and never
  print access or refresh tokens.

## Dependencies and validation

- Manage dependencies with uv; commit `pyproject.toml` and `uv.lock`; do not
  install dependencies with raw `pip`.
- For CLI changes, run the component checks documented in the
  [README](README.md#tests), including `uv run notes --help`.
