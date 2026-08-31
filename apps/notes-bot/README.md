For the Notes project, I’d treat the Telegram bot as a **thin conversational client over the same Notes platform**, not as a separate backend with duplicated business logic.

## 1. Goal

The Telegram bot should let a user work with personal notes without leaving Telegram:

- authenticate/link Telegram ↔ Supabase user;
- create notes quickly;
- list/retrieve/search notes;
- edit/archive/delete notes;
- manage tags;
- attach Telegram files/photos/documents to notes;
- later support semantic search, reminders, and AI actions.

The bot should remain deliberately small. Supabase owns identity and persistence; a future FastAPI service can own richer application/domain logic.

---

# 2. Recommended stack

```text
Python 3.14
uv
aiogram 3
httpx
Supabase
SQLite
pytest
ruff
```

Responsibilities:

```text
Telegram
   │
   ▼
aiogram bot
   │
   ├── Telegram interaction
   ├── command parsing
   ├── conversational state
   ├── account linking
   │
   ▼
Notes application/service layer
   │
   ▼
Supabase
 ├── Auth
 ├── PostgreSQL
 └── Storage
```

SQLite should remain **local bot infrastructure**, not the notes database.

Good SQLite use cases:

- pending link challenges;
- temporary login state;
- Telegram conversation state if persistence is required;
- rate-limit/cooldown metadata;
- ephemeral jobs.

Do not mirror notes into SQLite.

---

# 3. Architecture

I would evolve `apps/notes-bot` toward this structure:

```text
apps/notes-bot/
├── pyproject.toml
├── README.md
├── src/
│   └── notes_bot/
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       │
│       ├── bot/
│       │   ├── router.py
│       │   ├── commands/
│       │   │   ├── start.py
│       │   │   ├── help.py
│       │   │   ├── note.py
│       │   │   ├── notes.py
│       │   │   ├── search.py
│       │   │   ├── tags.py
│       │   │   └── account.py
│       │   ├── callbacks/
│       │   ├── middleware/
│       │   └── keyboards/
│       │
│       ├── application/
│       │   ├── auth_service.py
│       │   ├── notes_service.py
│       │   ├── tags_service.py
│       │   └── attachments_service.py
│       │
│       ├── infrastructure/
│       │   ├── supabase/
│       │   │   ├── auth.py
│       │   │   ├── notes.py
│       │   │   ├── tags.py
│       │   │   └── storage.py
│       │   └── sqlite/
│       │       ├── database.py
│       │       └── link_challenges.py
│       │
│       ├── web/
│       │   ├── server.py
│       │   ├── routes.py
│       │   └── templates/
│       │
│       └── models/
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

This does **not** mean you need to create all these modules now. It is the target shape.

---

# 4. Authentication

You already made the right architectural decision: **do not make Telegram identity itself the Supabase identity**.

Maintain:

```text
Telegram user
      │
      │ linking flow
      ▼
Supabase authenticated user
```

Conceptually you need a mapping such as:

```text
telegram_user_id
        ↓
supabase_user_id
```

I would eventually persist that mapping in PostgreSQL, for example:

```text
telegram_accounts

id
user_id            -> auth.users.id
telegram_user_id
telegram_chat_id
created_at
updated_at
```

with:

```text
UNIQUE telegram_user_id
UNIQUE user_id
```

depending on whether you want one or several Telegram accounts per user.

Your existing browser OTP flow is a good bootstrap:

```text
/start
   ↓
Generate link challenge
   ↓
Send browser URL
   ↓
User enters email
   ↓
Supabase OTP
   ↓
Verify OTP
   ↓
Consume challenge
   ↓
Associate Telegram account ↔ user
```

Once linked, Telegram commands no longer need interactive login.

---

# 5. Bot UX

Keep the command surface small.

### Basic commands

```text
/start
/help

/note
/notes
/search
/tags

/account
/logout
```

But Telegram should primarily work through **natural message shortcuts**, not commands.

For example:

```text
Buy milk tomorrow
```

could eventually mean:

```text
create note("Buy milk tomorrow")
```

Initially I would avoid ambiguity and use:

```text
/note Buy milk tomorrow
```

or a compact syntax:

```text
+ Buy milk tomorrow
```

Later the bot can infer intent.

---

# 6. Core MVP

The first useful product should be extremely small.

### Create

```text
/note Learn PostgreSQL indexes
```

Bot:

```text
Saved ✓

Learn PostgreSQL indexes
```

### List

```text
/notes
```

Bot:

```text
1. Learn PostgreSQL indexes
2. Call Alice
3. Kubernetes notes
```

Use inline buttons:

```text
[1] [2] [3]
[Next →]
```

### View

Selecting a note:

```text
Kubernetes notes

Pods are...
```

Buttons:

```text
[Edit] [Tags] [Archive]
[Delete]
```

### Search

```text
/search postgres
```

returns matching notes.

That alone makes the bot genuinely useful.

---

# 7. Application boundary

A handler should **not** contain Supabase queries.

Bad:

```python
@router.message(Command("notes"))
async def notes_handler(message):
    client.table("notes").select("*")...
```

Target:

```python
@router.message(Command("notes"))
async def notes_handler(message, notes_service):
    notes = await notes_service.list_notes(...)
```

Then:

```text
Telegram Handler
       ↓
NotesService
       ↓
NotesRepository
       ↓
Supabase
```

This becomes especially valuable because you are planning:

```text
Web
Mobile
CLI
TUI
Telegram
FastAPI
```

The concepts should converge rather than each client inventing its own data semantics.

---

# 8. Supabase access

There are two reasonable stages.

### Current/local stage

Bot talks directly to Supabase:

```text
Telegram bot → Supabase
```

This is perfectly acceptable while the application is small.

### Later production architecture

Once your FastAPI server becomes the canonical backend:

```text
Telegram Bot
Mobile
Web
CLI
TUI
   │
   ▼
Notes API
   │
   ▼
Supabase
```

Then the bot mostly becomes:

```text
Telegram UI adapter
```

I would **not move to FastAPI prematurely**. Direct Supabase access is currently simpler and helps you learn the platform.

---

# 9. Attachments

Telegram is particularly useful here.

A user could send:

```text
photo
PDF
voice message
document
```

and choose:

```text
[Create note]
[Attach to existing]
```

Pipeline:

```text
Telegram file
      ↓
download temporarily
      ↓
Supabase Storage
      ↓
note_attachments row
      ↓
delete local temp file
```

Never keep permanent Telegram files on the bot filesystem.

For your existing private `note-attachments` bucket, this fits very naturally.

---

# 10. Tags

Do not over-design the Telegram UI for tags.

Simple syntax:

```text
/note PostgreSQL indexes #database #postgres
```

Parser:

```text
title/body:
PostgreSQL indexes

tags:
database
postgres
```

Later support:

```text
/tags
/tag database
```

---

# 11. Conversation state

Some actions need multi-step interaction:

```text
Edit note
Attach file
Choose tags
Delete confirmation
Account linking
```

Model these as explicit states.

Example:

```text
IDLE
WAITING_FOR_NOTE_BODY
WAITING_FOR_EDIT_BODY
WAITING_FOR_ATTACHMENT_TARGET
WAITING_FOR_DELETE_CONFIRMATION
```

Avoid giant nested handler logic.

For short-lived state, aiogram FSM is enough.

For state that must survive restart, persist only the necessary metadata in SQLite.

---

# 12. Errors

Telegram needs much friendlier failures than a CLI.

Internally:

```text
AuthRequired
NoteNotFound
PermissionDenied
RateLimited
StorageFailure
SupabaseUnavailable
```

User-facing responses:

```text
Your Telegram account isn't linked yet.

/start to connect it.
```

or:

```text
I couldn't reach the Notes service.
Try again shortly.
```

Do not leak:

```text
PostgREST error
JWT
database policy names
stack traces
Supabase URLs
```

---

# 13. Security

Important invariants:

```text
Telegram user ID alone never grants database access.

Link challenge:
- cryptographically random
- hashed at rest
- expires
- one-time use

OTP:
- never log it

Supabase user:
- still constrained by RLS

Service-role key:
- avoid in bot where possible
```

Ideally normal notes operations execute with a user session/token so that **RLS remains the security boundary**.

That is preferable to:

```text
bot service role
+ manually filter user_id
```

because one forgotten filter becomes a data leak.

---

# 14. Testing strategy

Your current discipline with pytest/ruff is good for this app.

I would use three levels.

### Unit

No Telegram/Supabase network.

```text
command parsing
tag extraction
pagination
link challenge expiration
state transitions
error mapping
```

### Integration

Against local Supabase:

```text
link user
create note
list notes
update note
delete/archive
RLS isolation
attachment upload
```

Use the existing:

```text
roman@example.test
alice@example.test
```

to verify isolation.

### End-to-end

Actual Telegram is expensive and brittle, so keep only a few tests:

```text
/start → link
/note
/notes
/search
```

Most behavior should be testable below Telegram.

---

# 15. Observability

At minimum structured logs containing:

```text
event
telegram_user_id
command/action
duration
result
error_type
```

Never log:

```text
OTP
access token
refresh token
note contents by default
email unnecessarily
```

Later add:

```text
request_id
user_id
deployment/version
```

---

# 16. Deployment

The bot can ultimately be one container:

```text
notes-bot
```

with configuration through environment variables.

Example:

```text
TELEGRAM_BOT_TOKEN
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
NOTES_BOT_BASE_URL
NOTES_BOT_ENCRYPTION_KEY
DATABASE_PATH
LOG_LEVEL
```

Architecture on your future VPS:

```text
Internet
   │
   ├── Telegram
   │       │
   │       ▼
   │   notes-bot
   │
   └── HTTPS
           │
           ▼
         Caddy
           │
           ├── bot linking HTTP endpoint
           ├── Notes web app/API
           └── Supabase gateway
```

The bot itself can use either:

```text
long polling
```

or:

```text
webhook
```

Start with **long polling** locally.

Use webhook later if deployment makes it advantageous. There is no need to introduce it now.

---

# 17. Milestones

I would implement it in this order:

1. **Authentication/linking completion**
   - finalize OTP browser flow;
   - persist Telegram ↔ Supabase user relationship;
   - `/account`;
   - unlink/logout.

2. **Read-only notes**
   - `/notes`;
   - pagination;
   - view note;
   - `/search`.

3. **Create notes**
   - `/note <text>`;
   - multiline conversation;
   - basic tags.

4. **Mutations**
   - edit;
   - archive;
   - delete with confirmation.

5. **Tags**
   - list tags;
   - filter by tag;
   - add/remove tags.

6. **Attachments**
   - Telegram document/photo → Supabase Storage;
   - attach/list/remove.

7. **Bot UX polish**
   - inline keyboards;
   - pagination;
   - `/help`;
   - consistent messages;
   - error handling.

8. **Production**
   - Docker image;
   - health endpoint;
   - graceful shutdown;
   - structured logging;
   - deployment configuration;
   - CI.

9. **Advanced features**
   - voice note transcription;
   - semantic search;
   - AI summarization;
   - reminders;
   - conversational commands.

---

# 18. Features I would deliberately postpone

Do **not** add these to the MVP:

```text
LLM conversational agent
automatic intent detection
vector search
reminders
shared notes
Telegram groups
complex rich editor
background queues
RabbitMQ
Redis
Kubernetes-specific architecture
microservices
```

They are all interesting later, but they would obscure the important architecture you are building now.

---

## Target definition of “Telegram bot complete”

For the first production-quality release, I would call it finished when this journey works reliably:

```text
/start
   ↓
link existing Supabase account
   ↓
/note Read chapter 4 #books
   ↓
/notes
   ↓
open note
   ↓
edit/tag/archive/delete
   ↓
/search chapter
   ↓
send document → attach to note
```

with RLS isolation, restart-safe account linking, tests, Docker packaging, health checks, and no service-role bypass for normal note operations.

That gives you a **real Notes client**, while keeping the bot architecture small enough that the eventual FastAPI API can cleanly replace its direct Supabase repository layer.
