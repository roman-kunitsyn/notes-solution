For the Notes project, I’d keep the CLI deliberately thin: **Python + Typer as a human-friendly client of the same Supabase-backed notes system**, not a second implementation of business logic.

## 1. Goal

`notes-cli` should give you fast terminal access to:

- authentication
- notes CRUD
- tags
- search/filtering
- attachments
- import/export
- scripting-friendly output
- later, offline/local workflows if they become useful

Example UX:

```bash
notes auth login

notes add "Buy coffee"
notes add --title "Docker notes" --tag docker --tag devops

notes ls
notes ls --tag docker
notes show 42

notes edit 42
notes rm 42

notes search "kubernetes"

notes tags
notes tag add 42 python

notes export ./backup
```

The important architectural rule is:

> The CLI is a client of the Notes platform, not the place where Notes domain logic lives.

---

# 2. Technology stack

I’d use:

```text
Python 3.14
Typer
Rich
Supabase Python SDK
httpx
Pydantic
platformdirs
pytest
ruff
uv
```

Optional later:

```text
keyring          credentials/token storage
questionary      interactive prompts
orjson           large exports
textual          only if CLI evolves toward TUI
```

I would **not** add SQLAlchemy or a local database initially.

Your authoritative state is Supabase/PostgreSQL.

---

# 3. Suggested project structure

```text
apps/notes-cli/
├── pyproject.toml
├── README.md
├── src/
│   └── notes_cli/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       │
│       ├── commands/
│       │   ├── auth.py
│       │   ├── notes.py
│       │   ├── tags.py
│       │   ├── search.py
│       │   ├── attachments.py
│       │   └── export.py
│       │
│       ├── services/
│       │   ├── auth.py
│       │   ├── notes.py
│       │   ├── tags.py
│       │   └── attachments.py
│       │
│       ├── clients/
│       │   └── supabase.py
│       │
│       ├── models/
│       │   ├── note.py
│       │   └── tag.py
│       │
│       ├── config.py
│       ├── session.py
│       ├── output.py
│       ├── editor.py
│       └── errors.py
│
└── tests/
    ├── unit/
    └── integration/
```

Do not split it this far on day one. Start small and grow into this structure.

For the initial version:

```text
notes_cli/
├── app.py
├── config.py
├── client.py
├── auth.py
├── notes.py
└── output.py
```

is completely sufficient.

---

# 4. Command hierarchy

I’d design the command surface early because this becomes the stable public API of the CLI.

```text
notes
├── auth
│   ├── login
│   ├── logout
│   ├── status
│   └── whoami
│
├── add
├── ls
├── show
├── edit
├── rm
│
├── search
│
├── tag
│   ├── ls
│   ├── add
│   └── rm
│
├── attachment
│   ├── ls
│   ├── add
│   ├── get
│   └── rm
│
├── export
├── import
│
└── config
    ├── show
    └── path
```

I prefer:

```bash
notes add
notes ls
notes show
```

instead of:

```bash
notes note add
notes note list
notes note show
```

because notes are the primary resource.

Secondary resources deserve namespaces:

```bash
notes tag ...
notes attachment ...
notes auth ...
```

---

# 5. Note creation

Support progressively richer invocation.

Simple:

```bash
notes add "remember to renew domain"
```

Structured:

```bash
notes add \
  --title "Supabase deployment" \
  --tag supabase \
  --tag devops
```

Pipe input:

```bash
pbpaste | notes add --title "Clipboard"
```

Editor:

```bash
notes add --edit
```

or simply:

```bash
notes add
```

and if no body is supplied, `$EDITOR` opens.

That gives you excellent Unix ergonomics.

---

# 6. Listing notes

Default:

```bash
notes ls
```

Output:

```text
ID   UPDATED       TITLE                 TAGS
42   2m ago        Supabase deployment   supabase,devops
41   yesterday     Docker cheatsheet     docker
38   Aug 28        Meeting notes         work
```

Filters:

```bash
notes ls --tag docker
notes ls --limit 20
notes ls --since 7d
notes ls --sort created
notes ls --archived
```

Eventually:

```bash
notes ls --format json
```

This is extremely important.

Every data-producing CLI command should eventually support:

```text
table     human-readable
json      scripting/API
plain     simple shell pipelines
```

For example:

```bash
notes ls --format json | jq '.[] | .title'
```

---

# 7. `show`

```bash
notes show 42
```

Human output:

```text
Supabase deployment

Tags: supabase, devops
Created: 2026-08-30 20:42
Updated: 2026-08-31 01:14

Run migrations before restarting services...
```

Machine output:

```bash
notes show 42 --format json
```

Raw body:

```bash
notes show 42 --body
```

Then:

```bash
notes show 42 --body | pbcopy
```

becomes useful.

---

# 8. Editing

Use `$EDITOR`.

```bash
notes edit 42
```

Resolve editor roughly as:

```text
$VISUAL
$EDITOR
fallback: vi
```

You can also allow:

```bash
notes edit 42 --title "New title"
```

without launching an editor.

This distinction is useful for automation.

---

# 9. Authentication

Since the Notes platform already uses Supabase Auth, the CLI should use the same identity.

Commands:

```bash
notes auth login
notes auth logout
notes auth status
notes auth whoami
```

Possible login:

```text
Email: roman@example.test
Password:
```

Later you can support OTP:

```bash
notes auth login --otp
```

The CLI should persist only the session/token needed to restore authentication.

A sensible location:

```text
macOS:
~/Library/Application Support/notes-cli/

Linux:
~/.local/share/notes-cli/
```

using `platformdirs`.

Example:

```text
config.json
session.json
```

Eventually credentials could move to OS Keychain using `keyring`.

---

# 10. Configuration

Environment variables first:

```bash
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
```

Then optional persistent configuration:

```bash
notes config show
notes config path
```

Potential config:

```toml
supabase_url = "http://127.0.0.1:54321"
output = "table"
editor = "nvim"
page_size = 20
```

Avoid storing secrets that don't need to be stored.

The CLI must **never use `service_role` credentials**.

It behaves as a normal user, which means your existing RLS remains the security boundary.

---

# 11. Service architecture

Typer functions should stay very small.

Bad:

```python
@app.command()
def add(...):
    # authenticate
    # query supabase
    # manipulate DTO
    # format error
    # print result
```

Better conceptually:

```text
Typer command
       │
       ▼
NotesService
       │
       ▼
Supabase client
```

For example:

```text
notes add
    ↓
commands.notes.add()
    ↓
NotesService.create_note()
    ↓
Supabase
```

This makes tests easy and prevents CLI/UI logic from contaminating domain operations.

---

# 12. Models

Have explicit Python models even though Supabase returns dictionaries.

For example conceptually:

```text
Note
- id
- user_id
- title
- content
- created_at
- updated_at

Tag
- id
- name
```

Pydantic is useful at the boundary:

```text
Supabase JSON
      ↓
Pydantic model
      ↓
CLI formatting
```

That prevents schema drift from silently leaking everywhere.

---

# 13. Error handling

Centralize errors.

You want output like:

```text
Error: authentication required.
Run:

    notes auth login
```

not:

```text
postgrest.exceptions.APIError(...)
```

Have CLI-facing error categories like:

```text
AuthenticationError
NotFoundError
ValidationError
NetworkError
ConflictError
```

And convert low-level Supabase/httpx errors at the service/client boundary.

Exit codes should be stable eventually:

```text
0 success
1 generic failure
2 usage/validation
3 authentication
4 not found
5 network/service unavailable
```

Useful for scripting.

---

# 14. Search

Start with PostgreSQL filtering/search exposed by the existing database.

```bash
notes search docker
```

Later:

```bash
notes search docker --tag devops
notes search "postgres backup" --limit 10
```

Do **not** put embeddings/vector search into the CLI architecture itself.

If semantic search arrives later:

```bash
notes search "how did I configure storage?" --semantic
```

the CLI should simply call whatever search capability the backend/database exposes.

---

# 15. Attachments

Since the project already has a private Storage bucket, the CLI becomes particularly useful here.

```bash
notes attachment add 42 ./diagram.png
notes attachment ls 42
notes attachment get 42 diagram.png
notes attachment rm 42 diagram.png
```

RLS/Storage policies remain the security mechanism.

A nice later feature:

```bash
notes attachment add 42 -
```

for stdin, where appropriate.

---

# 16. Import/export

This should be one of the later milestones, not initial CRUD.

Export:

```bash
notes export ./notes-backup
```

Possible representation:

```text
notes-backup/
├── manifest.json
├── notes/
│   ├── 42.md
│   ├── 43.md
│   └── 44.md
└── attachments/
```

A Markdown note could contain front matter:

```yaml
---
id: 42
title: Supabase deployment
tags:
  - supabase
  - devops
created_at: ...
updated_at: ...
---
Note body...
```

That makes the backup both machine-readable and human-readable.

---

# 17. Testing strategy

Three layers are enough.

### Unit tests

Mock service dependencies.

Test:

```text
command parsing
formatting
validation
editor handling
config resolution
```

### Service tests

Mock Supabase client.

Test:

```text
create/update/delete behavior
response conversion
error translation
```

### Integration tests

Against local Supabase:

```text
login
create note
read note
edit note
tag note
delete note
attachment lifecycle
RLS isolation
```

The RLS integration test is particularly important:

```text
Roman creates note
Alice cannot see note
```

Your database tests may already prove this, but validating the client path is still valuable.

---

# 18. Milestones

I would develop it in this order.

## Milestone 0 — CLI skeleton

Implement:

```bash
notes --help
notes --version
```

Set up:

```text
uv
Typer
Ruff
pytest
src layout
```

---

## Milestone 1 — configuration + Supabase client

Support:

```text
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
```

Create one client factory.

Add:

```bash
notes config show
```

No note functionality yet.

---

## Milestone 2 — authentication

Implement:

```bash
notes auth login
notes auth logout
notes auth status
notes auth whoami
```

Persist/recover user session.

This establishes the entire security path.

---

## Milestone 3 — minimum Notes CRUD

Implement:

```bash
notes add
notes ls
notes show
notes rm
```

At this point the CLI is already useful.

---

## Milestone 4 — editor workflow

Implement:

```bash
notes add --edit
notes edit ID
```

Support:

```text
$VISUAL
$EDITOR
```

This is what makes it pleasant as a real notes CLI.

---

## Milestone 5 — tags and filtering

```bash
notes tag ls
notes tag add
notes tag rm

notes ls --tag
notes search
```

---

## Milestone 6 — output modes

Add consistently:

```bash
--format table
--format json
--format plain
```

Then make sure things like this work:

```bash
notes ls --format json | jq ...
```

---

## Milestone 7 — attachments

Integrate private Supabase Storage.

---

## Milestone 8 — import/export

Human-readable Markdown backup/restore.

---

## Milestone 9 — CLI polish

Add:

```text
completion
better error messages
pagination
timestamps
confirmations
--yes
NO_COLOR
config defaults
```

Generate shell completions:

```bash
notes --install-completion
```

Typer gives you much of this automatically.

---

# 19. Things I would intentionally postpone

Do not initially add:

```text
local SQLite note mirror
offline synchronization
plugin architecture
TUI
daemon
background synchronization
embeddings
AI commands
complex config profiles
multiple accounts
custom API abstraction
```

All of those can be good features, but they attack different problems.

Your first CLI should essentially be:

```text
Typer
  ↓
small service layer
  ↓
Supabase SDK
  ↓
RLS-protected Notes database
```

That is enough.

---

# 20. Long-term relationship with the other Notes clients

This becomes important because you're planning several clients.

```text
                      ┌─ Next.js Web
                      │
                      ├─ React Native
                      │
Supabase/Postgres  ◀──┼─ Python CLI
                      │
                      ├─ Telegram Bot
                      │
                      ├─ Textual TUI
                      │
                      └─ FastAPI API
```

The CLI should **not depend on the FastAPI server initially**.

Because Supabase already gives you:

```text
Auth
PostgREST
Storage
RLS
```

there's little value in:

```text
CLI → FastAPI → Supabase
```

for ordinary CRUD.

Use the future FastAPI service only when you introduce operations that genuinely need server-side orchestration.

---

# 21. Definition of the first genuinely useful release

I would call `v0.1` done when this workflow works:

```bash
notes auth login

notes add --title "CLI works" --tag test

notes ls

notes show <id>

notes edit <id>

notes search CLI

notes rm <id>

notes auth logout
```

With:

```text
✓ RLS isolation
✓ session persistence
✓ useful errors
✓ $EDITOR support
✓ table output
✓ JSON output
✓ unit tests
✓ local Supabase integration tests
✓ ruff clean
```

That gives you a small, production-shaped CLI without prematurely turning it into a framework.

Given your wider Notes architecture, I’d make **authentication → CRUD → `$EDITOR` → tags/search → JSON output → attachments → export/import** the implementation sequence.
