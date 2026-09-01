# Notes

<<<<<<< HEAD
`notes-solution` is the repository for Notes, a personal notes product built on
Supabase. The Notes CLI is the functional reference client for the currently
supported product baseline.

## Supported today

- Authentication
- Notes CRUD
- Private note attachments

Tags and rich search are future capabilities. New capabilities normally
stabilize in the CLI before they propagate to other clients.

## Start here

- [Product baseline](docs/product.md)
- [Documentation index](docs/README.md)
- [Notes CLI](apps/notes-cli/README.md)
- [Notes Telegram bot](apps/notes-bot/README.md)
- [Self-hosted Supabase with Docker Compose](deploy/self-hosted/README.md)

The Telegram bot currently supports secure account linking; it does not yet
support Notes CRUD. Self-hosted Supabase is available through Docker Compose.
Kubernetes is not a current capability.
||||||| bdd41ec
For this project, I’d make the repository root the **coordination layer**, not another application. Each client/service stays independently runnable, while the root defines shared conventions, commands, documentation, CI, and infrastructure.

A good target structure for the Notes/Supabase monorepo is:

```text
notes-solution/
├── AGENTS.md
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
│
├── .editorconfig
├── .gitignore
├── .env.example
├── Makefile
│
├── apps/
│   ├── notes-web/
│   ├── notes-mobile/
│   ├── notes-cli/
│   ├── notes-tui/
│   └── notes-bot/
│
├── services/
│   └── notes-api/
│
├── packages/
│   └── ...
│
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   ├── seed.sql
│   ├── tests/
│   └── templates/
│
├── deploy/
│   ├── self-hosted/
│   ├── docker/
│   └── kubernetes/
│
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── development/
│   ├── deployment/
│   ├── decisions/
│   └── agents/
│
├── scripts/
│   ├── dev/
│   ├── test/
│   └── ci/
│
└── .github/
    └── workflows/
```

The important distinction is:

```text
apps/
```

contains user-facing clients such as Next.js, Expo, Textual, CLI, and Telegram bot.

```text
services/
```

contains independently deployable backend services such as the FastAPI API.

```text
packages/
```

is only for code genuinely shared by multiple applications. I would **not create shared packages prematurely**. Duplication is cheaper than accidentally coupling Python, TypeScript, mobile, and web applications through an abstraction that turns out to be wrong.

At the root, I’d establish these responsibilities.

| File / directory     | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| `README.md`          | Project entry point and basic developer workflow |
| `AGENTS.md`          | Rules for Codex/agents working anywhere in repo  |
| `ARCHITECTURE.md`    | System-level architecture and boundaries         |
| `CONTRIBUTING.md`    | Development workflow and quality gates           |
| `.env.example`       | Root-level environment variable reference        |
| `Makefile`           | Human-friendly common commands                   |
| `docs/`              | Longer-lived project knowledge                   |
| `scripts/`           | Reproducible automation                          |
| `.github/workflows/` | CI/CD                                            |
| `supabase/`          | Canonical database/backend platform definition   |
| `deploy/`            | Deployment infrastructure                        |

I would deliberately avoid introducing a heavyweight monorepo manager. You have several ecosystems:

```text
Python   → uv
Node.js  → npm/pnpm
Expo     → Node ecosystem
Supabase → Supabase CLI
Docker   → Docker/Compose
K8s      → kubectl manifests/Helm later
```

Trying to force all of them through Turborepo, Nx, Poetry workspaces, etc. buys relatively little. The repository itself is the monorepo; a small root `Makefile` is enough to coordinate it.

For example, the intended developer UX should eventually look approximately like:

```bash
make help

make supabase-start
make supabase-stop
make supabase-reset

make bot-test
make api-test
make cli-test

make test
make lint
make check
```

And the most valuable root command should be:

```bash
make check
```

which becomes the local equivalent of CI.

Conceptually:

```text
check
├── formatting checks
├── linters
├── Python tests
├── TypeScript checks
├── Supabase/database tests
└── git diff --check
```

Not every app has to exist before this command exists. Add checks as applications appear.

For documentation, I’d keep the first version small:

```text
docs/
├── product/
│   └── overview.md
│
├── architecture/
│   ├── system.md
│   └── authentication.md
│
├── development/
│   └── local-development.md
│
├── deployment/
│   └── overview.md
│
└── decisions/
    └── README.md
```

Then each significant application gets its own local docs where appropriate:

```text
apps/notes-bot/
├── AGENTS.md
├── README.md
└── ...
```

The rule should be:

```text
root AGENTS.md
    ↓ inherited by everything

apps/notes-bot/AGENTS.md
    ↓ adds bot-specific rules
```

That gives Codex a useful hierarchy rather than one enormous agent instruction file.

For your project specifically, I’d define the system boundary roughly as:

```text
                  ┌─────────────────┐
                  │    Supabase     │
                  │                 │
                  │ PostgreSQL      │
                  │ Auth            │
                  │ Storage         │
                  │ Realtime        │
                  │ REST            │
                  └────────┬────────┘
                           │
            ┌──────────────┼───────────────┐
            │              │               │
       notes-web       notes-api       notes-bot
            │              │               │
       Next.js          FastAPI          Python
            │
      notes-mobile
          Expo

       notes-cli
         Python

       notes-tui
        Textual
```

The important architectural rule is that **Supabase is the platform/backend of record**. The FastAPI service should exist because some use cases need application-specific server logic, not because every client must go through FastAPI.

That lets you compare different architectural styles experimentally:

```text
Web ───────────► Supabase
CLI ───────────► Supabase
Bot ───────────► Supabase

Mobile ────────► Supabase

Some operation:
Client ────────► FastAPI ────────► Supabase
```

That fits the workshop nature of this repository very well.

For initial root setup, I would do it in **four milestones**, rather than creating everything at once.

1. **Repository foundation** — root docs, `.editorconfig`, `.gitignore`, `.env.example`, `Makefile`, directory conventions.
2. **Agent foundation** — root `AGENTS.md`, documentation conventions, task boundaries, quality gates.
3. **Unified developer workflow** — `make check`, `make test`, Supabase lifecycle commands, existing Python app checks.
4. **CI foundation** — reproduce `make check` in GitHub Actions, then progressively add app-specific jobs.

Because several applications are still being built, I would **not** create empty boilerplate implementations for all of them. Empty directories or documented planned components are enough until implementation begins.

For Codex, I’d start the root-project work with this task:

# Task: Establish the monorepo root project foundation

Work at the repository root.

The repository is a multi-client Notes system built around Supabase. Existing and planned components include:

- `supabase/` — database, Auth, Storage, migrations, seeds, and database tests
- `apps/notes-cli/` — Python CLI
- `apps/notes-bot/` — Python Telegram bot
- `apps/notes-web/` — planned Next.js + TypeScript web client
- `apps/notes-mobile/` — planned React Native + Expo client
- `apps/notes-tui/` — planned Python + Textual client
- `services/notes-api/` — planned Python + FastAPI service
- `deploy/` — self-hosted Supabase, Docker, and later Kubernetes deployment assets

The repository root should act as the coordination layer for the monorepo rather than as an application.

## Goal

Establish a minimal, production-quality root foundation that gives humans and coding agents a clear project structure and consistent development workflow without introducing unnecessary monorepo tooling.

## First inspect

Before making changes:

1. Inspect the existing repository tree.
2. Read existing root documentation and configuration.
3. Inspect existing app-level tooling and commands.
4. Do not overwrite useful existing conventions.
5. Identify which proposed files/directories already exist.

## Root structure

Move toward this structure where appropriate:

```text
/
├── AGENTS.md
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── .editorconfig
├── .gitignore
├── .env.example
├── Makefile
├── apps/
├── services/
├── packages/
├── supabase/
├── deploy/
├── docs/
├── scripts/
└── .github/
```

Do not create empty application implementations merely to satisfy this tree.

Do not introduce Turborepo, Nx, Poetry workspaces, or another monorepo manager.

Existing ecosystem-native tools remain authoritative:

- Python: `uv`
- JavaScript/TypeScript: existing package manager
- Supabase: Supabase CLI
- Containers: Docker/Compose
- Kubernetes: kubectl/manifests when introduced

## Root documentation

Create or improve:

### `README.md`

It should explain:

- what the Notes project is;
- high-level repository structure;
- major components;
- prerequisites;
- basic local-development workflow;
- how to find deeper documentation.

Keep it concise and useful as the repository entry point.

### `ARCHITECTURE.md`

Document:

- Supabase as the core backend platform;
- clients and services as independently runnable components;
- direct client-to-Supabase access where appropriate;
- FastAPI as an application service for operations that require server-side logic rather than a mandatory proxy for every request;
- component boundaries;
- high-level data/auth flow.

Do not invent functionality that does not exist.

### `CONTRIBUTING.md`

Document:

- environment setup expectations;
- branch/change workflow;
- formatting, linting, and testing expectations;
- requirement to run the repository quality checks before completion;
- principle that component-specific commands remain owned by that component.

## Documentation directories

Create only useful initial documentation structure:

```text
docs/
├── product/
├── architecture/
├── development/
├── deployment/
└── decisions/
```

Avoid placeholder documents with no useful content.

Add `docs/decisions/README.md` explaining the lightweight ADR convention if appropriate.

## Root Makefile

Provide a small root `Makefile` as the human-friendly orchestration interface.

At minimum consider targets such as:

```text
help
check
test
lint
format-check
supabase-start
supabase-stop
supabase-reset
```

Only wire commands that can be correctly derived from the existing repository.

Do not fake commands for components that do not exist yet.

`make check` should become the canonical aggregate local quality gate and should invoke existing checks where practical.

Keep Make targets simple wrappers around ecosystem-native commands rather than implementing complex build logic.

## Environment documentation

Review existing environment-variable usage.

Create or improve root `.env.example` only where it provides useful cross-project documentation.

Never include secrets.

Do not unnecessarily duplicate app-specific environment variables if those apps already maintain their own `.env.example`; reference them instead.

## Git/editor defaults

Review and minimally improve:

- `.gitignore`
- `.editorconfig`

Do not replace mature existing files unnecessarily.

## Rules

- Prefer small, explicit configuration.
- Avoid speculative abstractions.
- Avoid adding dependencies unless required.
- Do not create shared packages until actual shared code requires them.
- Preserve existing working application behavior.
- Do not modify production secrets.
- Do not perform unrelated refactoring.
- Do not create placeholder application code.
- Documentation must describe current reality and clearly label planned components.

## Verification

Run all applicable existing project checks after the changes.

At minimum include the currently applicable Python/Supabase checks and:

```bash
git diff --check
```

If a root `make check` target is introduced, run it as part of verification.

## Final response

Report:

1. files created;
2. files modified;
3. root conventions established;
4. commands exposed through the Makefile;
5. checks run and results;
6. any intentionally deferred root setup;
7. final `git status --short`.

Do not commit the changes.

After that task, I’d make the **root `AGENTS.md` its own dedicated Codex task**, because it deserves careful design rather than being casually generated together with boilerplate.
=======
`notes-solution` is the repository umbrella for Notes, a self-hosted personal
notes product built on Supabase.

The current functional reference client is the CLI. It supports authentication,
Notes CRUD, and private file attachments. Tags and richer search are planned,
not currently supported product capabilities.

## Start here

- [Repository workflow for contributors and agents](AGENTS.md)
- [Development guide](docs/development.md)
- [Product baseline](docs/product.md)
- [Architecture](docs/architecture.md)
- [Roadmap](ROADMAP.md)
- [Documentation index](docs/README.md)
- [Notes CLI](apps/notes-cli/README.md)
- [Notes bot](apps/notes-bot/README.md) — account linking, private note CRUD,
  and private attachment delivery for linked accounts.
- [Self-hosted Supabase deployment](deploy/self-hosted/README.md)
>>>>>>> documentation
