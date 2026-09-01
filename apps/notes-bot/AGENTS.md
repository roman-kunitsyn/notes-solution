# Notes bot local instructions

Follow the shared [repository instructions](../../AGENTS.md). This file covers
only constraints specific to `apps/notes-bot/`. Planned client work is in the
[bot roadmap](ROADMAP.md).

## Telegram

- Keep Telegram handling limited to the implemented account-linking flow.
- Issue account-linking URLs only from private chats; never treat a Telegram
  user ID alone as authorization for Notes data.
- Keep user-facing failures safe and concise. Do not expose Supabase errors,
  session details, tokens, or internal exception text.

## OTP and link challenges

- Use cryptographically random link tokens and persist only their hashes.
- Keep challenges expiring and single-use; preserve the one-active-challenge
  behavior, email binding, OTP-request cooldown, and failed-attempt limit.
- Keep the token in the browser URL fragment so it is not sent in requests for
  the link page.
- Request email OTPs with `should_create_user=False` unless product
  requirements explicitly change that policy.
- Never log or persist OTP values, access tokens, refresh tokens, or
  authentication headers.

## Linked sessions and SQLite

- Encrypt refresh tokens before writing them to SQLite; retain restrictive
  database directory and file permissions.
- Refresh a linked session with the configured publishable or legacy anonymous
  key, and reject or remove sessions that Supabase rejects or whose returned
  identity differs from the linked user.
- Keep SQLite limited to bot-local link challenges and linked sessions. Notes
  data remains in Supabase and must use user-authenticated access protected by
  RLS; never use a secret or service-role key for normal user operations.

## HTTP security

- Keep the HTTP surface limited to health and browser account linking; it is
  not a general Notes API.
- Validate request JSON, field types, and link-token format. Return stable,
  non-sensitive errors and suitable status codes.
- Preserve `no-store`, restrictive CSP, no-referrer, anti-framing, and
  nosniff headers on the linking flow. Do not place authentication tokens in
  browser storage, server responses, logs, or inline script handlers.
