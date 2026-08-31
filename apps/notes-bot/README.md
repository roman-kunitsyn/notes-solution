# Notes Telegram bot

The Notes Telegram bot is the account-linking client for the self-hosted Notes
product. It does not currently provide Notes CRUD, search, tags, attachments,
or a deployment package.

## Current functionality

- Starts a Telegram bot with long polling and handles `/start` in private
  chats.
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

Copy `.env.example` into an environment file or otherwise set its variables.
`NOTES_BOT_ENCRYPTION_KEY` must be a URL-safe base64 key encoding 32 bytes;
generate one with:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For local development, `SUPABASE_URL` defaults to the local API endpoint in
`.env.example`. `NOTES_BOT_BASE_URL` may use HTTP only for localhost; a public
linking URL must use HTTPS.

## Run

```bash
uv run notes-bot
```

The process starts the HTTP server and Telegram long polling. By default the
HTTP server listens on `127.0.0.1:8080`; set `NOTES_BOT_HTTP_HOST` and
`NOTES_BOT_HTTP_PORT` to change the binding.

## Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run notes-bot --help
```
