# Development guide

This guide helps contributors navigate the repository. Shared working rules
are in the [root agent instructions](../AGENTS.md); component commands and
local constraints remain with each component.

## Repository layout

- `apps/notes-cli/` — the functional command-line reference client.
- `apps/notes-bot/` — the Telegram account-linking client with private Notes
  creation, listing, viewing, and editing.
- `supabase/` — local Supabase configuration, schema migrations, seed data,
  and database tests.
- `deploy/self-hosted/` — Docker-based self-hosted Supabase deployment.
- `docs/` — product and repository documentation.

## Setup and checks

There is no root setup, test, lint, or quality-gate command: the root
[`Makefile`](../Makefile) is currently empty. Start in the component you are
changing, read its local instructions, and use the commands documented there.

For any file, first follow the root [agent instructions](../AGENTS.md), then
read each `AGENTS.md` on the path from the repository root to that file. A
child instruction file adds to or overrides the shared rules for its directory
and descendants. The current component-specific instruction files are:

- [Notes CLI setup and checks](../apps/notes-cli/README.md)
- [Notes CLI local instructions](../apps/notes-cli/AGENTS.md)
- [Notes bot setup and checks](../apps/notes-bot/README.md)
- [Notes bot local instructions](../apps/notes-bot/AGENTS.md)
- [Supabase backend lifecycle, migrations, and database tests](../supabase/README.md)
- [Self-hosted Supabase deployment](../deploy/self-hosted/README.md)
- [Production deployment guide](../deploy/self-hosted/docs/production-deployment.md)

Use the root workflow for inspect, plan, implementation, validation, and the
completion report. Use component documentation for exact setup and validation
commands.

## Configuration policy

The [root agent instructions](../AGENTS.md#configuration) define the shared
configuration policy. In short, applications consume runtime environment with
the following precedence:

```text
explicit runtime environment > local .env values > safe code defaults
```

Required values have no default and must fail fast. `.env` files are ignored
local-development conveniences; production, Docker/Compose, CI/CD, and future
Kubernetes deployments inject configuration explicitly. Child project READMEs
own their variable lists and defaults, so this guide intentionally does not
repeat them.
