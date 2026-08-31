For an agent working on `apps/notes-bot`, I would keep the documentation set small, explicit, and operational. The goal is not to document everything; it is to give the agent enough context to make correct changes without repeatedly rediscovering architecture, product intent, and constraints.

I would use this set:

```text
apps/notes-bot/
├── AGENTS.md
├── README.md
└── docs/
    ├── PRODUCT.md
    ├── ARCHITECTURE.md
    ├── AUTH.md
    ├── DATA.md
    ├── TELEGRAM_UX.md
    ├── DEVELOPMENT.md
    ├── TESTING.md
    ├── DEPLOYMENT.md
    └── ROADMAP.md
```

The important part is what belongs in each document.

## `AGENTS.md`

This is the **agent operating manual**.

It should contain rules such as:

```text
scope
coding conventions
security invariants
architecture rules
testing requirements
commands to run
things agents must not do
definition of done
```

This is the file Codex should read first.

You already have a good basis for this one.

---

## `README.md`

This should answer:

> What is this application, and how do I run it?

Keep it practical.

Suggested sections:

```md
# Notes Telegram Bot

## Purpose

## Features

## Architecture Overview

## Requirements

## Installation

## Environment Variables

## Run Locally

## Run Tests

## Project Structure

## Common Commands

## Documentation
```

Do not turn `README.md` into the architecture specification.

It should mostly be an entry point.

---

# `docs/PRODUCT.md`

This tells the agent **what we are building**.

This is very important because without it an agent will often implement technically correct but product-wrong behavior.

Suggested contents:

```md
# Product

## Product Goal

## Target User

## Core User Jobs

## Bot Responsibilities

## Non-Goals

## Core Features

### Account linking

### Create note

### List notes

### Search notes

### Edit note

### Delete/archive note

### Tags

### Attachments

## User Journeys

## Product Rules

## Error Experience

## MVP Definition

## Future Features
```

For example:

```text
The Telegram bot is a thin client for the Notes platform.

It is not:
- the canonical Notes backend;
- a general AI assistant;
- a second database;
- a replacement for Supabase Auth.
```

This one statement can prevent a lot of architectural drift.

---

# `docs/ARCHITECTURE.md`

This tells the agent **how the application is structured**.

I would make this one of the strongest documents.

Include:

```text
system context
application boundaries
module responsibilities
dependency direction
request flows
external services
local state
future migration path
```

For example:

```text
Telegram
    │
    ▼
Handlers
    │
    ▼
Application Services
    │
    ▼
Repositories / Adapters
    │
    ├── Supabase Auth
    ├── PostgREST
    ├── Storage
    └── SQLite
```

And explicitly define dependency direction:

```text
bot -> application -> infrastructure
```

not:

```text
infrastructure -> Telegram handlers
```

Also describe the HTTP side:

```text
Browser
   ↓
HTTP routes
   ↓
AuthService
   ↓
Supabase Auth
```

And the future direction:

```text
Current:
Telegram Bot → Supabase

Possible future:
Telegram Bot → Notes API → Supabase
```

This tells the agent not to prematurely build the future architecture.

---

# `docs/AUTH.md`

For this project, I would absolutely keep authentication in its own document.

Authentication is complex enough that burying it in `ARCHITECTURE.md` is dangerous.

Document the actual state machine.

For example:

```text
Telegram user
    ↓
/start
    ↓
create link challenge
    ↓
browser /link?token=...
    ↓
validate token
    ↓
enter email
    ↓
request Supabase OTP
    ↓
enter OTP
    ↓
verify OTP
    ↓
associate Telegram account with Supabase user
    ↓
consume challenge
```

Include the endpoints:

```text
GET  /health
GET  /link
POST /link/validate
POST /link/request-otp
POST /link/verify-otp
```

And document invariants:

```text
should_create_user = false

challenge:
- random
- hashed
- expiring
- single-use

OTP:
- never persisted
- never logged

normal operations:
- user-authenticated
- RLS enforced
```

Also add a section:

```md
## Failure Cases

- expired challenge
- consumed challenge
- invalid OTP
- Supabase unavailable
- rate limited
- Telegram account already linked
```

This document will save enormous agent-token usage later.

---

# `docs/DATA.md`

Document what data lives where.

This is particularly useful because this bot has **two persistence systems**.

Start with a clear rule:

```text
Supabase/PostgreSQL = application data
SQLite = bot-local temporary infrastructure state
```

Then document relevant entities.

For example:

```text
Supabase

profiles
notes
tags
note_tags
note_attachments
telegram_accounts
```

and:

```text
SQLite

link_challenges
```

For each important table, you do not need a full SQL dump.

Something like this is enough:

```md
## link_challenges

Purpose:
Temporary browser-linking challenge.

Fields:

- token_hash
- telegram_user_id
- telegram_chat_id
- created_at
- expires_at
- consumed_at

Rules:

- token itself is never stored
- challenge is single-use
- expired challenges cannot be consumed
```

Also document ownership:

```text
notes.user_id → auth.users.id

All user-owned data is protected by RLS.
```

---

# `docs/TELEGRAM_UX.md`

This is extremely useful for agent implementation because Telegram handlers otherwise become inconsistent very quickly.

Document commands and expected behavior.

Example:

```md
# Telegram UX

## Commands

/start
/help
/account

/note
/notes
/search
/tags
```

For each:

```md
## /note

Input:

/note Learn PostgreSQL indexes

Success:

Saved ✓

Learn PostgreSQL indexes

Failure:

Your account is not linked.
Use /start to connect it.
```

Also document callback patterns:

```text
note:view:<id>
note:edit:<id>
note:archive:<id>
note:delete:<id>
```

If you use them.

Then specify UX conventions:

```text
short messages
no technical errors
confirmation before destructive actions
pagination instead of giant messages
inline keyboards for actions
```

This becomes almost like a UI contract.

---

# `docs/DEVELOPMENT.md`

This document tells the agent **how to work in the repo**.

Suggested contents:

```md
# Development

## Requirements

Python 3.14
uv
Supabase CLI
Docker/Colima

## Setup

uv sync

## Local Supabase

supabase start

## Run Bot

...

## Run HTTP Server

...

## Environment

...

## Useful Commands

...

## Code Style

...

## Adding a Dependency

...

## Database Migrations
```

Include exact commands whenever possible.

For example:

```bash
uv sync

uv run notes-bot

uv run pytest

uv run ruff format .
uv run ruff check .
```

An agent should not need to guess how to launch the project.

---

# `docs/TESTING.md`

This should explain **what tests exist and what must be tested**.

I recommend making a clear testing pyramid.

```text
unit
integration
e2e
```

Document where each belongs.

Example:

```md
## Unit Tests

No external network.

Examples:

- challenge expiration
- OTP error mapping
- command parsing
- callback parsing
- pagination
```

```md
## Integration Tests

Use local Supabase.

Test users:

roman@example.test
alice@example.test
```

Then document the key security test:

```text
Roman must never be able to access Alice's notes.
Alice must never be able to access Roman's notes.
```

And the standard verification command:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest -W error::ResourceWarning
git diff --check
```

This is important because an agent otherwise decides its own arbitrary definition of "tested."

---

# `docs/DEPLOYMENT.md`

Initially this can be small.

Document:

```text
local execution
Docker target
environment variables
health checks
long polling
future webhook option
shutdown behavior
persistent SQLite volume/path
Supabase connectivity
```

Architecture:

```text
Telegram
    ↓
notes-bot container
    │
    ├── Supabase
    └── SQLite volume

Browser
    ↓
Caddy
    ↓
notes-bot HTTP server
```

Do not put Kubernetes details here yet unless they are actually implemented.

You can later extend it.

---

# `docs/ROADMAP.md`

Keep this very short.

It should tell the agent what exists, what is next, and what is intentionally postponed.

For example:

```md
# Roadmap

## Completed

- HTTP health endpoint
- link challenge persistence
- browser OTP request
- browser OTP verification
- local mail capture
- existing-user-only OTP

## Current

- complete Telegram account association

## Next

1. /account
2. /notes
3. /note
4. /search
5. edit/archive/delete
6. tags
7. attachments

## Later

- Docker production packaging
- webhook
- Notes API integration
- voice transcription
- semantic search

## Explicitly Deferred

- LLM agent
- Redis
- RabbitMQ
- Kubernetes application logic
```

This is particularly valuable for Codex because it prevents it from "helpfully" implementing features from later milestones.

---

# How these documents work together

The agent's reading order should effectively be:

```text
AGENTS.md
    ↓
PRODUCT.md
    ↓
ARCHITECTURE.md
    ↓
task-specific document
```

For example, if implementing OTP:

```text
AGENTS.md
PRODUCT.md
ARCHITECTURE.md
AUTH.md
TESTING.md
```

If implementing `/notes`:

```text
AGENTS.md
PRODUCT.md
ARCHITECTURE.md
DATA.md
TELEGRAM_UX.md
TESTING.md
```

If implementing Docker:

```text
AGENTS.md
ARCHITECTURE.md
DEVELOPMENT.md
DEPLOYMENT.md
```

The agent does **not** need to read every document for every task.

---

# One more document I would avoid

I would not create something like:

```text
TECHNICAL_SPECIFICATION.md
SYSTEM_SPECIFICATION.md
DESIGN.md
IMPLEMENTATION.md
BACKEND.md
SUPABASE.md
BOT.md
```

all at once.

Those usually overlap heavily.

The cleaner model is:

```text
PRODUCT    = why / what
ARCHITECTURE = system shape
AUTH       = security-sensitive flow
DATA       = persistence
TELEGRAM_UX = user interaction contract
DEVELOPMENT = how to run/change it
TESTING    = how correctness is proven
DEPLOYMENT = how it runs
ROADMAP    = where development is going
AGENTS     = how the agent must behave
```

That is enough.

## Recommended final set

For this project specifically, I would create exactly these ten files:

```text
apps/notes-bot/
├── AGENTS.md
├── README.md
└── docs/
    ├── PRODUCT.md
    ├── ARCHITECTURE.md
    ├── AUTH.md
    ├── DATA.md
    ├── TELEGRAM_UX.md
    ├── DEVELOPMENT.md
    ├── TESTING.md
    ├── DEPLOYMENT.md
    └── ROADMAP.md
```

The **highest-value five** for Codex are `AGENTS.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `AUTH.md`, and `TESTING.md`. Those alone give an agent a strong mental model of the project; the others reduce rediscovery as the bot grows.
