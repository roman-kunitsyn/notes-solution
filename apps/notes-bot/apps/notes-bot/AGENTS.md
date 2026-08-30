# Notes Bot Agent Guide

This file applies to everything under `apps/notes-bot/`.

## Purpose

`notes-bot` is a production-oriented Telegram frontend for the Notes application backed by Supabase.

Develop it incrementally as a practical workshop. Prefer small, complete vertical slices over large frameworks or speculative abstractions.

All development and verification must remain local until external deployment is explicitly requested.

## Working Method

Before making changes:

1. Inspect the relevant implementation, tests, and configuration.
2. Check the repository status and preserve existing user work.
3. Understand existing interfaces before changing signatures.
4. Consult current official documentation when working with Supabase, aiogram, aiohttp, or security-sensitive APIs.

When implementing:

- Make the smallest change that completes the requested behavior.
- Follow existing naming, module boundaries, dependency injection, and error-handling patterns.
- Avoid unrelated refactoring.
- Do not extract a shared Python package until concrete duplication between the CLI and bot justifies it.
- Explain each meaningful change in English.
- Do not deploy or contact external production infrastructure unless explicitly requested.

After implementing:

1. Run focused tests for the changed component.
2. Run formatting and linting.
3. Run the complete test suite.
4. Check for resource leaks and malformed diffs.
5. Report changed files, behavior, tests, and remaining concerns.

## Technology

The intentional runtime is Python 3.14.

Use the existing project tools and dependencies:

- `uv` for dependency management and command execution
- `aiogram` for Telegram bot handling
- `aiohttp` for the local HTTP linking server
- `supabase-py` asynchronous client for Supabase access
- SQLite for bot-owned linking and session state
- `cryptography`/Fernet for refresh-token encryption
- `pytest` and `pytest-asyncio` for tests
- Ruff for formatting and linting

Do not replace these tools or add another framework without a demonstrated requirement.

Dependencies must remain version-constrained, and `uv.lock` must stay committed.

## Architecture Boundaries

Keep responsibilities separated:

- Telegram handlers manage Telegram input and responses.
- HTTP handlers manage browser requests and safe HTTP responses.
- OTP services coordinate Supabase Auth with local OTP state.
- Session services refresh and provide authenticated Supabase clients.
- SQLite modules own persistence and transactions.
- Supabase/PostgREST clients perform note operations.
- Supabase RLS remains the authorization boundary.

HTTP and Telegram handlers should call services rather than reproduce authentication, persistence, or Supabase logic.

Prefer dependency injection for services and clients so tests do not require real credentials or network access.

Do not introduce a service container, repository framework, global mutable registry, or unnecessary base classes.

## Supabase Security Model

These rules are mandatory:

- Clients may use only a Supabase publishable key or legacy anonymous key.
- Never use, expose, log, or request a secret key or service-role key.
- Telegram identity is not Supabase identity.
- A Telegram user must prove control of an existing Supabase account before linking.
- OTP sign-in must use `should_create_user=False`.
- The bot must not silently create Supabase accounts.
- Authorization belongs in Supabase RLS.
- Never bypass RLS to simplify bot implementation.
- Never send `user_id` when creating user-owned resources; ownership must come from `auth.uid()`.
- Validate the Supabase user returned by authentication before persisting a session.
- Store refresh tokens only in encrypted form.
- Persist rotated refresh tokens.
- Never persist access tokens unless a demonstrated requirement is reviewed first.
- Challenge consumption and linked-session storage must remain atomic.
- Do not use Telegram usernames, names, or profile metadata for authorization.
- Do not use user-editable Supabase metadata for authorization.

Never log or expose:

- Telegram bot tokens
- Supabase keys
- Encryption keys
- OTP values
- Raw link-challenge tokens
- Access tokens
- Refresh tokens
- Full authentication URLs containing secrets
- User email addresses unless explicitly required and safely redacted

Public errors must not reveal whether a Supabase account exists.

## Linking Flow

The browser-linking flow uses these principles:

- Generate challenges with a cryptographically secure random source.
- Store only a hash of each challenge token.
- Put the raw challenge token in the URL fragment, not the query string.
- Remove the fragment from browser history before sending the token to the server.
- Challenges must expire.
- Challenges must be single-use.
- A new challenge invalidates the previous active challenge for that Telegram user.
- A challenge binds to one Telegram user and chat.
- Once an email is bound to a challenge, it cannot switch to another email.
- OTP requests have a cooldown.
- Invalid OTP attempts are limited.
- Network and infrastructure failures must not count as invalid OTP attempts.
- Invalid or expired OTP responses from Supabase do count as failed attempts.
- Successful linking stores the encrypted refresh token and consumes the challenge in one SQLite transaction.

Preserve existing HTTP security headers. Do not weaken Content Security Policy or add inline scripts merely for convenience.

## SQLite Rules

SQLite contains bot-internal state, not application authorization policy.

Use the existing migration mechanism and increment `PRAGMA user_version` for schema changes.

For ordinary operations, use the closing context manager:

```python
with database_connection(database_path) as connection:
    ...
```

Do not use `with open_database(...)`, because the standard SQLite connection context manager commits or rolls back but does not close the connection.

For explicit transactions such as `BEGIN IMMEDIATE`, use:

```python
connection = open_database(database_path)

try:
    connection.execute("BEGIN IMMEDIATE")
    ...
    connection.commit()
except Exception:
    connection.rollback()
    raise
finally:
    connection.close()
```

Do not replace an explicit `sqlite3.Connection` with the `database_connection()` context-manager object.

Use parameterized SQL. Never construct SQL with untrusted string interpolation.

Keep database directory and file permissions restrictive.

## Error Handling

Distinguish among:

- Invalid user input
- Invalid, expired, or consumed link state
- OTP cooldown or attempt exhaustion
- Supabase Auth rejection
- Network or temporary upstream failure
- Invalid or incomplete upstream responses
- Internal persistence failure

Translate these into safe domain errors before they reach Telegram or HTTP responses.

Do not expose raw exception messages to users.

Preserve exception causes with `raise ... from error` where useful for diagnostics.

Do not broadly retry authentication or persistence operations. Retries must be explicit, bounded, and safe.

## HTTP API

HTTP endpoints must:

- Validate content type and request structure.
- Validate field presence and types.
- Use small JSON responses.
- Never return secrets or internal exceptions.
- Use appropriate status codes.
- Return `429` and `Retry-After` for cooldowns when available.
- Return a safe temporary-failure response for unavailable upstream services.
- Avoid account-enumeration differences in messages.
- Preserve existing security headers.
- Avoid real Supabase calls in unit tests.

Keep request bodies small. Do not add cookies or browser session state unless a concrete requirement is reviewed.

## Telegram Behavior

Sensitive account operations must work only in private chats.

Telegram handlers must safely handle missing user or chat information.

Messages should be concise and should not expose internal identifiers or authentication details.

Do not trust Telegram commands, callback data, usernames, or chat state as proof of Supabase authentication.

## Testing

Tests must be deterministic and independent.

Use:

- `tmp_path` for SQLite databases
- Generated Fernet keys for encryption tests
- `AsyncMock` or small fakes for Supabase and Telegram clients
- Fixed timestamps when expiry or cooldown behavior is under test
- No real Telegram, SMTP, Supabase, or internet calls in unit tests
- Integration markers for tests requiring the local Supabase stack

Every security-sensitive behavior should include failure-path tests.

Important cases include:

- Two-user isolation
- Expired and consumed challenges
- Email mismatch
- OTP cooldown
- OTP attempt exhaustion
- Delivery failure rollback
- Invalid OTP counting
- Network failures not counting
- Missing or malformed Auth responses
- Supabase identity mismatch
- Refresh-token rotation
- Atomic session linking
- Duplicate link conflicts
- Resource cleanup
- Safe public error responses

Do not weaken assertions merely to make a test pass. First determine whether the implementation or the expectation is wrong.

## Validation Commands

Run focused tests first, followed by the full checks:

```bash
uv run pytest <relevant-test-file> -v
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run pytest -W error::ResourceWarning
git diff --check
```

Run integration tests only when the required local services and explicitly local test configuration are available.

Do not use production credentials in tests.

## Scope Control

Do not perform external deployment, DNS changes, SMTP configuration, VPS changes, GitHub secret changes, releases, or destructive database operations unless explicitly requested.

Do not commit, push, create tags, or open pull requests unless explicitly requested.

Do not modify `apps/notes-cli`, Supabase migrations, deployment configuration, or workflows unless the current task requires it and the scope has been confirmed.

When a requested change would cross one of these boundaries, stop and explain what additional decision or authorization is required.
