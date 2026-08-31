# AGENTS.md

## Scope

This file applies to the Telegram Notes bot located in:

```text
apps/notes-bot/
```

The bot is one client of the larger Notes platform.

Its responsibilities are:

- Telegram interaction;
- Telegram account linking;
- user authentication flow;
- note CRUD operations;
- note search;
- tag management;
- attachment handling;
- small amounts of bot-specific local state;
- bot-related HTTP endpoints such as account linking and health checks.

The bot must remain a thin application client around the shared Notes/Supabase platform.

Do not turn this application into a separate general-purpose backend.

---

# Technology

Use the existing project stack unless a task explicitly requires otherwise.

Primary technologies:

```text
Python 3.14
uv
aiogram 3
Supabase
PostgreSQL
Supabase Auth
Supabase Storage
SQLite
httpx
pytest
ruff
```

Follow versions and dependencies already defined in `pyproject.toml`.

Do not add dependencies when the standard library or an existing dependency solves the problem adequately.

---

# Project Principles

## Keep the bot thin

Telegram handlers should primarily:

1. parse Telegram input;
2. validate simple interaction-level constraints;
3. call application services;
4. format the result;
5. send the Telegram response.

Do not put database queries or large amounts of business logic directly into handlers.

Preferred flow:

```text
Telegram handler
        ↓
Application service
        ↓
Repository / infrastructure adapter
        ↓
Supabase
```

---

## Supabase is the primary data store

Persistent Notes application data belongs in Supabase/PostgreSQL.

Examples:

- notes;
- tags;
- note/tag relationships;
- user profiles;
- Telegram-to-user account mappings;
- attachment metadata.

Do not duplicate this data into SQLite.

---

## SQLite is bot-local infrastructure

SQLite may store small amounts of temporary or bot-specific state.

Appropriate examples:

- account-link challenges;
- temporary authentication state;
- one-time tokens;
- cooldown information;
- restart-safe conversational state when necessary.

Do not use SQLite as a second Notes database.

---

# Authentication and Security

Authentication is security-sensitive.

Preserve the existing account-linking architecture unless the task explicitly requires changing it.

Conceptually:

```text
Telegram user
      ↓
link challenge
      ↓
browser authentication
      ↓
Supabase Auth
      ↓
Telegram account ↔ Supabase user
```

Important invariants:

- a Telegram user ID alone must not grant database access;
- account-link tokens must be cryptographically random;
- store link tokens hashed when persistence is required;
- link challenges must expire;
- link challenges must be single-use;
- OTP values must never be logged;
- access tokens and refresh tokens must never be logged;
- secrets must not be returned in HTTP responses;
- normal user operations should remain protected by Supabase RLS;
- do not use the Supabase service-role key for normal user operations when a user-authenticated session can be used instead.

Do not weaken authentication behavior merely to make tests easier.

---

# Existing Authentication Behavior

The project may include browser-based OTP authentication endpoints such as:

```text
GET  /health
GET  /link
POST /link/validate
POST /link/request-otp
POST /link/verify-otp
```

Preserve existing endpoint semantics and security properties unless the task explicitly changes them.

Supabase OTP requests for account linking should not silently create arbitrary new users unless product requirements explicitly allow that behavior.

When modifying the OTP flow, pay particular attention to:

- expired challenges;
- consumed challenges;
- invalid tokens;
- invalid OTP codes;
- retry cooldowns;
- rate limiting;
- temporary Supabase failures;
- browser refreshes;
- replay attempts.

---

# RLS

Supabase Row Level Security is part of the application's security boundary.

Never replace RLS with code such as:

```python
.select("*").eq("user_id", user_id)
```

and assume this is sufficient authorization.

Application-level filters may exist for correctness or performance, but authorization must remain enforced by RLS.

When changing database-facing behavior, consider whether existing RLS tests still prove isolation between users.

---

# Telegram Handlers

Keep handlers small and predictable.

Prefer:

```python
async def handler(message, service):
    result = await service.do_something(...)
    await message.answer(format_result(result))
```

Avoid:

```python
async def handler(message):
    # auth handling
    # SQL/PostgREST calls
    # parsing
    # validation
    # business rules
    # formatting
    # file handling
    # retries
```

Large handlers should be decomposed.

---

# Telegram UX

User-facing messages should be concise and understandable.

Do not expose implementation details such as:

- PostgreSQL errors;
- PostgREST response internals;
- stack traces;
- JWT errors;
- database policy names;
- Supabase project URLs;
- internal exception classes.

Translate internal failures into stable user-facing messages.

For example:

```text
Your Telegram account is not linked yet.
Use /start to connect it.
```

or:

```text
The Notes service is temporarily unavailable.
Please try again.
```

Keep detailed errors in application logs, subject to secret-redaction rules.

---

# Application Services

Business operations should preferably live behind application-level services.

Examples:

```text
AuthService
NotesService
TagsService
AttachmentsService
```

Services should describe application operations rather than Telegram concepts.

Prefer:

```text
notes_service.create_note(...)
notes_service.search_notes(...)
notes_service.archive_note(...)
```

instead of:

```text
telegram_service.handle_note_command(...)
```

This keeps domain behavior reusable and testable independently of Telegram.

---

# Infrastructure Boundaries

Infrastructure-specific code should be isolated when practical.

Examples:

```text
Supabase Auth
PostgREST
Supabase Storage
SQLite
Telegram API
HTTP server
```

Do not leak raw SDK response shapes deeply into application logic.

Normalize important results into project-owned models or simple data structures where useful.

Avoid adding abstraction layers that do not yet provide concrete value.

---

# Notes Operations

Core operations may include:

```text
create
get
list
search
update
archive
delete
```

Preserve ownership semantics.

A user must never be able to access another user's notes through:

- note IDs;
- search;
- pagination;
- callbacks;
- attachment IDs;
- tags;
- crafted Telegram callback data.

Treat every client-provided identifier as untrusted.

---

# Tags

Tags should remain part of the Notes domain rather than Telegram-specific storage.

Possible Telegram syntax such as:

```text
/note Learn PostgreSQL #database #postgres
```

may be parsed by the bot, but persistence belongs in Supabase.

Tag parsing should be deterministic and unit-testable.

Do not introduce an NLP or LLM dependency merely to parse tags.

---

# Attachments

Telegram attachments may include:

- documents;
- photos;
- audio;
- voice messages.

Persistent attachment files should be stored in Supabase Storage.

Typical flow:

```text
Telegram
   ↓
temporary local download
   ↓
Supabase Storage
   ↓
attachment metadata in PostgreSQL
   ↓
remove temporary local file
```

Rules:

- avoid permanent local attachment storage;
- clean temporary files reliably;
- enforce reasonable file-size constraints;
- validate ownership before attaching files to a note;
- do not make private Storage objects publicly accessible as a shortcut.

---

# Conversation State

Use explicit state when interactions span multiple Telegram messages.

Examples:

```text
waiting_for_note_body
waiting_for_edit_body
waiting_for_attachment_target
waiting_for_delete_confirmation
```

Prefer explicit finite states to boolean combinations or deeply nested handler conditions.

Use in-memory/FSM state for short-lived interactions when restart persistence is not needed.

Persist state only when losing it during restart would create meaningful correctness or security problems.

---

# HTTP Server

The bot may expose a small HTTP server for:

- health checks;
- account linking;
- browser OTP flow;
- webhook handling if introduced later.

Keep this server narrow.

Do not gradually turn it into the general Notes API. The Notes API is a separate application concern.

HTTP handlers should follow the same architecture:

```text
HTTP route
   ↓
application service
   ↓
infrastructure
```

Validate all external input.

Use appropriate response status codes.

Do not return sensitive internal error details.

---

# Configuration

Configuration should come from environment variables or existing configuration abstractions.

Examples may include:

```text
TELEGRAM_BOT_TOKEN
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
NOTES_BOT_BASE_URL
NOTES_BOT_ENCRYPTION_KEY
DATABASE_PATH
LOG_LEVEL
```

Rules:

- do not hard-code secrets;
- do not commit production credentials;
- do not add fallback production secrets;
- fail clearly when required configuration is missing;
- keep test configuration explicit.

When introducing a new environment variable, update relevant documentation and tests.

---

# Logging

Logs should help diagnose behavior without leaking private information.

Useful fields include:

```text
event
telegram_user_id
operation
duration
result
error_type
```

Do not log:

```text
OTP codes
access tokens
refresh tokens
Telegram bot token
encryption keys
service-role keys
full authentication headers
private note bodies by default
```

Prefer structured, concise logging over arbitrary debug prints.

Do not leave `print()` debugging statements in production code.

---

# Error Handling

Use explicit domain/application errors where they improve behavior.

Examples:

```text
AuthenticationRequired
LinkChallengeExpired
LinkChallengeConsumed
NoteNotFound
PermissionDenied
RateLimited
StorageUnavailable
```

Do not catch broad exceptions without a reason.

Avoid:

```python
except Exception:
    return None
```

unless the abstraction intentionally converts all failures and the original error is appropriately handled/logged.

Preserve exception context where useful.

---

# Async Code

The bot is asynchronous.

Do not introduce blocking network or filesystem operations into the event loop without considering their impact.

Prefer async-compatible libraries already used by the project.

Keep async boundaries clear.

Do not add unnecessary concurrency.

If multiple operations must be performed concurrently, consider:

- failure semantics;
- ordering;
- cancellation;
- cleanup.

Correctness is more important than maximizing concurrency.

---

# Python Style

Target Python 3.14.

Use modern Python syntax where it improves clarity.

Prefer:

- type annotations;
- small functions;
- explicit return types on public functions;
- dataclasses or project models for structured data when useful;
- `pathlib.Path` for filesystem paths;
- context managers for resources;
- clear dependency injection instead of globals.

Avoid unnecessary metaprogramming and framework-like abstractions.

Do not write compatibility workarounds for unsupported older Python versions unless explicitly requested.

---

# Tests

All meaningful behavior changes should include or update tests.

Use:

```text
pytest
```

Prefer testing behavior rather than implementation details.

## Unit tests

Appropriate for:

- parsing;
- tag extraction;
- state transitions;
- pagination;
- expiration logic;
- error mapping;
- formatting;
- token/challenge logic.

Unit tests should not require network access.

---

## Integration tests

Use local Supabase where necessary.

Important integration scenarios include:

- authenticating an existing user;
- linking Telegram and Supabase accounts;
- creating notes;
- listing notes;
- searching notes;
- updating notes;
- archiving/deleting notes;
- attachment operations;
- RLS isolation.

Where appropriate, verify isolation using two distinct test users.

Do not weaken production code to make integration testing easier.

---

## End-to-End Tests

Keep true Telegram/browser end-to-end tests limited to high-value flows.

Examples:

```text
/start → link account
create note
list notes
search
```

Most functionality should remain testable without contacting Telegram.

---

# Quality Checks

Before considering a task complete, run the relevant project checks.

From the repository root, typically:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest -W error::ResourceWarning
git diff --check
```

If the task only affects a narrow area, focused tests may be run during development, but the full relevant test suite should run before final completion when practical.

Do not ignore failing tests that are related to the change.

Do not modify tests merely to make incorrect behavior pass.

---

# Ruff

Code must remain compatible with the repository Ruff configuration.

Prefer fixing the underlying design rather than adding unnecessary:

```python
# noqa
```

or broad per-file ignores.

If suppression is genuinely necessary, keep it narrow and document the reason where it is not obvious.

---

# Resource Management

Tests are run with `ResourceWarning` treated as errors.

Ensure that resources are properly closed:

- HTTP clients;
- SQLite connections;
- files;
- temporary files;
- sockets;
- async tasks.

Prefer context managers and deterministic cleanup.

---

# Database Changes

Do not modify production database structure directly from application code.

Schema changes belong in Supabase migrations.

When a bot feature requires a schema change:

1. identify the required database change;
2. add or modify the appropriate migration;
3. preserve RLS;
4. update tests;
5. verify migrations against local Supabase.

Do not create ad-hoc tables automatically during normal bot startup unless they are explicitly bot-local SQLite tables.

SQLite schema migrations should be explicit and versioned.

---

# Supabase Usage

Use existing Supabase integration patterns before introducing new clients or wrappers.

Do not create a new Supabase client per trivial operation unless that is already the intended lifecycle.

When working with authenticated users:

- preserve their authentication context;
- avoid accidentally falling back to anonymous access;
- do not use administrative credentials as a convenience.

Handle external service failures explicitly.

---

# Dependencies

Before adding a dependency:

1. verify the requirement cannot be handled cleanly by the standard library;
2. check whether an existing dependency already provides the functionality;
3. evaluate maintenance and security implications;
4. keep the dependency narrowly scoped.

Do not add major frameworks for small utilities.

---

# Architecture Discipline

Prefer simple boundaries over speculative abstractions.

Good:

```text
handler
service
repository
```

Potential over-engineering:

```text
command bus
event bus
generic repository framework
dependency container framework
CQRS
plugin system
microservices
```

Do not introduce these without a concrete requirement.

The project should remain easy to read.

---

# Future Architecture

The current bot may communicate directly with Supabase.

A future architecture may introduce a shared FastAPI Notes API:

```text
Telegram
Web
Mobile
CLI
TUI
   ↓
Notes API
   ↓
Supabase
```

Do not prematurely restructure the bot around an API that does not yet exist.

However, keep application boundaries clean enough that replacing the Supabase repository with an HTTP API adapter later is straightforward.

---

# Out of Scope by Default

Unless explicitly requested, do not add:

- LLM agents;
- automatic intent detection;
- vector search;
- RabbitMQ;
- Redis;
- Kubernetes-specific behavior;
- event sourcing;
- shared/group notes;
- reminder systems;
- background job frameworks;
- complex plugin systems.

These may be added in future milestones but are not part of the base bot architecture.

---

# Agent Workflow

When given a task:

1. inspect the relevant existing code first;
2. understand current behavior and tests;
3. identify the smallest coherent change;
4. preserve public behavior unless the task changes it;
5. implement the change;
6. add/update focused tests;
7. run focused tests;
8. run formatting/linting;
9. run the broader relevant test suite;
10. inspect the final diff.

Do not rewrite unrelated code.

Do not perform opportunistic refactors unless they are necessary for the task.

If a larger architectural problem is discovered, report it separately rather than silently expanding scope.

---

# Task Scope

Prefer completing one coherent feature at a time.

Examples:

```text
implement /notes pagination
```

is a good task.

```text
redesign the bot, authentication, database, deployment, and UX
```

should be decomposed before implementation.

Keep diffs reviewable.

---

# Existing Code Is Authoritative

This document describes architectural intent, but the current repository is the source of truth for existing behavior.

Before changing anything:

- inspect the implementation;
- inspect tests;
- inspect configuration;
- inspect nearby patterns.

Do not assume filenames, classes, endpoints, or schemas exist merely because they appear as examples in this document.

If this document and tested repository behavior disagree, preserve working tested behavior unless the task explicitly requires migration to the documented design.

---

# Completion Report

At the end of a coding task, provide a concise report containing:

```text
What changed
Tests/checks run
Any important architectural/security notes
Remaining blockers, if any
```

Do not provide a long narrative unless requested.

If blocked, state:

- the exact blocker;
- evidence for it;
- the smallest next action needed.

Do not invent successful verification that was not actually performed.
