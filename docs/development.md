# Development guide

This guide helps contributors navigate the repository. Shared working rules
are in the [root agent instructions](../AGENTS.md); component commands and
local constraints remain with each component.

## Repository layout

- `apps/notes-cli/` — the functional command-line reference client.
- `apps/notes-bot/` — the Telegram account-linking client and future Notes
  client.
- `supabase/` — local Supabase configuration, schema migrations, seed data,
  and database tests.
- `deploy/self-hosted/` — Docker-based self-hosted Supabase deployment.
- `docs/` — product and repository documentation.

## Setup and checks

There is no root setup, test, lint, or quality-gate command: the root
[`Makefile`](../Makefile) is currently empty. Start in the component you are
changing, read its local instructions, and use the commands documented there.

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
