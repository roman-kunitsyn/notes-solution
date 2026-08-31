# Notes architecture

## Current system

Notes is a Supabase-backed personal notes product. Supabase is the system of
record for application data and identity:

- PostgreSQL stores Notes data;
- Supabase Auth authenticates users;
- Row Level Security (RLS) restricts data access to its owner; and
- Supabase Storage holds private note attachments.

Clients access Supabase directly with a publishable or legacy anonymous key
and the authenticated user's session. The database defaults and RLS policies
derive ownership from `auth.uid()` rather than trusting client-supplied owner
identifiers; clients do not act as a privileged application layer.

## Clients

Each client is independently runnable and connects to the same Supabase
project. The Notes CLI is the current functional reference client. The Notes
bot is a separate client for account linking.

There is no required FastAPI or other intermediary service in the current
architecture.

## Deployment boundary

The supported self-hosted deployment is the repository's Docker Compose
Supabase stack. Kubernetes is not part of the current deployment architecture.

## Related documentation

- [Product baseline](product.md)
- [Supabase backend guide](../supabase/README.md)
- [Self-hosted deployment](../deploy/self-hosted/README.md)
- [Production deployment runbook](../deploy/self-hosted/docs/production-deployment.md)
