# Notes CLI

The stable reference client for the self-hosted Supabase Notes application.
Other Notes clients follow its supported contract: authenticated Notes CRUD and
private file attachments, with Supabase Row Level Security (RLS) enforcing
per-user access.

## Documentation

- [Repository overview](../../README.md)
- [Product baseline](../../docs/product.md)
- [CLI roadmap](ROADMAP.md)
- [Development guide](../../docs/development.md)

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

The CLI normally reads this saved local configuration. At runtime,
`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` override the saved URL and
publishable (or legacy anonymous) key independently; neither has a code
default. `NOTES_CLI_CONFIG_DIR` is an optional safe override for the
platform configuration directory, primarily useful for isolated tests. The
CLI does not load `.env` files itself; local development tooling may supply
dotenv values to the process, while explicit runtime variables take precedence.
Never supply a Supabase secret or service-role key.

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

## Notes commands

```bash
uv run notes list
uv run notes list --limit 20
uv run notes show NOTE_ID

uv run notes create \
  --title "Workshop note" \
  --content "Created from Notes CLI."

uv run notes create --editor
uv run notes edit NOTE_ID --editor
uv run notes delete NOTE_ID --yes
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

The supported command surface is:

```text
notes version
notes config set|show|path|clear
notes login|logout|whoami
notes list|show|create|edit|delete
notes attach|attachments|download|detach
```

Tags, search, filtering beyond `list --limit`, alternate output formats, and
import/export are not current CLI behavior. See the [CLI roadmap](ROADMAP.md)
for planned work.

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
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run notes --help
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
