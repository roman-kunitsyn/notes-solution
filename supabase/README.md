# Supabase backend

This directory is the backend of record for Notes: local Supabase
configuration, database migrations, deterministic development fixtures, and
database-level tests. It supports the product baseline described in the
[product documentation](../docs/product.md); it is not a separate API service
or a Kubernetes deployment.

Start with the [repository entry point](../README.md), shared contributor
[instructions](../AGENTS.md), and repository [roadmap](../ROADMAP.md). Database
rules for changes in this directory are in [AGENTS.md](AGENTS.md), and planned
backend work is in [ROADMAP.md](ROADMAP.md).

## Local lifecycle

Run these commands from the repository root with the Supabase CLI installed.
The CLI reads [config.toml](config.toml), which enables local Auth, Storage,
database migrations, and the `seed.sql` fixture.

```sh
supabase start
supabase status
supabase stop
```

`supabase start` runs the local development stack; its local API, database,
Studio, and mail-testing ports are defined in [config.toml](config.toml).
Use `supabase status` to obtain the running service URLs and credentials.
`supabase stop` stops the local stack. This local setup is for development;
the supported self-hosted deployment is documented separately in
[deploy/self-hosted](../deploy/self-hosted/README.md).

## Schema and migrations

Committed SQL migrations in [migrations](migrations) define the schema,
indexes, triggers, Data API grants, RLS policies, and private attachment-bucket
policies. Create every schema or policy change in a new migration:

```sh
supabase migration new descriptive_change_name
```

Apply the complete migration history to a clean local database with:

```sh
supabase db reset --local
```

The reset also loads [seed.sql](seed.sql), because `db.seed.sql_paths` in
[config.toml](config.toml) points to it. The seed users and content are local
fixtures only, not production accounts or production data.

The schema contains `tags` and `note_tags` for future work, but tags are not
part of the current supported Notes baseline. See the [product baseline](../docs/product.md)
for the supported capability boundary.

## Ownership, RLS, and Storage

Database ownership is established by database defaults and RLS using
`auth.uid()`; it does not trust a client-supplied ownership identifier. The
ownership defaults are defined in
[20260827231420_add_ownership_defaults.sql](migrations/20260827231420_add_ownership_defaults.sql),
and the table policies are in
[20260827200631_create_notes_schema.sql](migrations/20260827200631_create_notes_schema.sql).

Note attachments live in the private `note-attachments` bucket. The bucket and
its Storage policies require paths in the form `<user-id>/<note-id>/<filename>`
and restrict access to a note owned by the authenticated user. See
[20260827233214_create_note_attachments.sql](migrations/20260827233214_create_note_attachments.sql).

## Database tests

After the local stack is running and has been reset, run the pgTAP suite:

```sh
supabase test db --local
```

The tests in [tests/database](tests/database) simulate authenticated JWT claims
and verify RLS isolation and `auth.uid()` ownership defaults. Run the focused
path when iterating on one area:

```sh
supabase test db --local tests/database/notes_rls_test.sql
supabase test db --local tests/database/ownership_defaults_test.sql
```

For the underlying Supabase CLI workflows, see the official
[database migrations guide](https://supabase.com/docs/guides/local-development/database-migrations)
[database testing guide](https://supabase.com/docs/guides/database/testing),
and [product security guidance](https://supabase.com/docs/guides/security/product-security).
