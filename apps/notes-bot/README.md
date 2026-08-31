# Notes Telegram bot

The Notes Telegram bot is the account-linking client for the self-hosted Notes
product. It can create, list, view, edit, and delete a linked account's notes,
and list their private attachments, but does not yet provide search, tags,
attachment upload/download/deletion, or a deployment package.

## Current functionality

- Starts a Telegram bot with long polling and handles `/start` in private
  chats.
- Lists the 20 most recently updated notes for a linked account with `/notes`
  in a private chat.
- Views one linked account note with `/note NOTE_ID` in a private chat.
- Lists private attachments for one linked account note with
  `/attachments NOTE_ID` in a private chat.
- Creates a linked account note with `/create TITLE`, with optional content on
  the following lines, in a private chat.
- Replaces a linked account note's title and content with
  `/edit NOTE_ID`, followed by the title and optional content on following
  lines, in a private chat.
- Deletes a linked account note with `/delete NOTE_ID` in a private chat.
- Issues a browser link for an existing Notes account.
- Sends and verifies email OTPs through Supabase Auth without creating users.
- Stores a linked Supabase refresh token encrypted in a bot-local SQLite
  database; linked-session support refreshes the session through Supabase.
- Exposes `GET /health` and the narrow browser linking flow:
  `GET /link`, `POST /link/validate`, `POST /link/request-otp`, and
  `POST /link/verify-otp`.

The link token is carried in the URL fragment, stored only as a hash, expires,
and is single-use. The SQLite database is local bot state, not a Notes data
store.

`/notes`, `/note`, `/attachments`, `/create`, `/edit`, and `/delete` use the
linked user's refreshed Supabase session and the existing RLS policies. They do
not persist or mirror Notes data locally. `/attachments` lists metadata only;
it does not download attachment contents.

## Documentation

- [Repository overview](../../README.md)
- [Product baseline](../../docs/product.md)
- [Bot roadmap](ROADMAP.md)
- [Development guide](../../docs/development.md)

## Requirements

- Python supported by `pyproject.toml`
- [uv](https://docs.astral.sh/uv/)
- A Telegram bot token
- A running Notes Supabase deployment and a publishable or legacy anonymous
  key

Never configure the bot with a Supabase secret or service-role key.

## Development setup

```bash
cd apps/notes-bot
uv sync --locked --all-groups
uv run notes-bot --help
```

Copy `.env.example` to an ignored local `.env` and set its values for local
development. Start the bot with `uv run --env-file .env notes-bot` so `uv`
supplies those values to the process. The bot itself reads runtime environment
variables and does not discover or load `.env` files. Explicit runtime values
take precedence over values from the explicitly supplied local dotenv file.

| Variable | Required | Purpose and safe default |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot credential. |
| `SUPABASE_URL` | Yes | Supabase API URL; local example is `http://127.0.0.1:54321`. |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Publishable or legacy anonymous API key; secret and service-role keys are rejected. |
| `NOTES_BOT_BASE_URL` | Yes | Public browser-linking base URL; HTTP is allowed only for localhost. |
| `NOTES_BOT_ENCRYPTION_KEY` | Yes | URL-safe base64 key encoding exactly 32 bytes. |
| `NOTES_BOT_DATABASE_PATH` | No | SQLite path; defaults to the platform data directory. |
| `NOTES_BOT_HTTP_HOST` | No | Bind host; defaults to `127.0.0.1`. |
| `NOTES_BOT_HTTP_PORT` | No | HTTP port; defaults to `8080`. |

Generate `NOTES_BOT_ENCRYPTION_KEY` with:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`NOTES_BOT_BASE_URL` may use HTTP only for localhost; a public linking URL
must use HTTPS. Missing required configuration causes startup to fail with a
clear error.

## Run

```bash
uv run --env-file .env notes-bot
```

The process starts the HTTP server and Telegram long polling. By default the
HTTP server listens on `127.0.0.1:8080`; set `NOTES_BOT_HTTP_HOST` and
`NOTES_BOT_HTTP_PORT` to change the binding. Production, CI, containers, and
Kubernetes must inject configuration explicitly and should not pass a local
dotenv file.

## Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run notes-bot --help
```
