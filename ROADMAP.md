# Notes roadmap

This is the product and repository roadmap. Component roadmaps refine their
own implementation work without changing this cross-component order.

## Completed

| Date | Status | Outcome |
| --- | --- | --- |
| 2026-08 | Complete | Supabase Notes baseline established with Auth, RLS, and private attachments. |
| 2026-08 | Complete | CLI reference client delivers authenticated Notes CRUD and attachment operations. |

## Current

### Maintain supported CLI behavior

**In progress.** Stabilize the supported CLI interface, including its Notes
CRUD, authentication, attachment behavior, and validation coverage. This is
the reference behavior for subsequent clients.

### Deliver equivalent Notes CRUD in the bot

**Complete.** The bot can create, list, view, edit, and delete notes for a
linked account against the same Supabase-backed product.

## Parallel work

### Progress container infrastructure

**In progress.** Continue improving the Docker Compose-based self-hosted
deployment and its production operations in parallel with client work.

## Later

### Evaluate Kubernetes

**Future.** Kubernetes is deferred platform work. It is not a supported
deployment target and does not block the current Docker Compose path.

## Related documentation

- [Product baseline](docs/product.md)
- [CLI roadmap](apps/notes-cli/ROADMAP.md)
- [Bot roadmap](apps/notes-bot/ROADMAP.md)
- [Self-hosted deployment](deploy/self-hosted/README.md)
- [Production deployment runbook](deploy/self-hosted/docs/production-deployment.md)
