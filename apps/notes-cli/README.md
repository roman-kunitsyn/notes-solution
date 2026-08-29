# Notes CLI

A command-line client for the self-hosted Supabase Notes application.

It supports authenticated note management and private file attachments while
Supabase Row Level Security controls access to each user's data.

## Requirements

- Python supported by `pyproject.toml`
- [uv](https://docs.astral.sh/uv/)
- A running Notes Supabase deployment
- A Supabase publishable key or legacy anonymous key

Never configure the CLI with a secret key or service-role key.

## Development setup

```bash
cd apps/notes-cli
uv sync --locked --all-groups
uv run notes --help
```

## Configuration

```bash
uv run notes config set
uv run notes config show
uv run notes config path
```

The CLI prompts for the Supabase URL and API key.

For local self-hosting, the URL is normally:

```text
http://127.0.0.1:8000
```

Configuration and sessions are stored in the platform-specific user
configuration directory with restricted file permissions.

## Authentication

```bash
uv run notes login
uv run notes whoami
uv run notes logout
```

## Notes

```bash
uv run notes list
uv run notes show NOTE_ID

uv run notes create \
  --title "Workshop note" \
  --content "Created from Notes CLI."

uv run notes create --editor
uv run notes edit NOTE_ID --editor
uv run notes delete NOTE_ID
```

The editor workflow uses `$VISUAL` or `$EDITOR`. For example:

```bash
export EDITOR=nvim
uv run notes create --editor
```

## Attachments

```bash
uv run notes attach NOTE_ID ./document.pdf
uv run notes attachments NOTE_ID

uv run notes download \
  NOTE_ID \
  document.pdf \
  --output ./document.pdf

uv run notes detach NOTE_ID document.pdf
```

Attachments are private. Their Storage paths have this form:

```text
<user-id>/<note-id>/<filename>
```

The current bucket accepts PNG, JPEG, PDF, and plain-text files up to 10 MiB.

## Tests

Run unit tests:

```bash
uv run pytest -m "not integration"
```

Run the end-to-end integration test while the local Supabase stack is running:

```bash
uv run pytest -m integration
```

Run linting:

```bash
uv run ruff check .
```

Run everything:

```bash
uv run ruff check .
uv run pytest
```

## Build

```bash
uv build
```

This creates a source archive and wheel under `dist/`.

## Install as a command

From `apps/notes-cli`:

```bash
uv tool install --force .
```

The command then works outside the repository:

```bash
notes --help
notes version
```

If uv reports that its executable directory is missing from `PATH`, run:

```bash
uv tool update-shell
```

Then start a new shell.

## Shell completion

```bash
notes --install-completion
```

Start a new shell after installing completion.

## Security model

- The CLI uses a publishable or legacy anonymous API key.
- The API key identifies the application; the user's access token identifies
  the authenticated user.
- Notes and attachments are protected by Supabase RLS policies.
- The CLI does not send `user_id` when creating owned resources.
- Secret and service-role keys must never be used because they can bypass RLS.
