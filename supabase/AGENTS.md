# Supabase component instructions

Follow the shared [repository workflow](../AGENTS.md) and the component
[README](README.md). This file adds rules for database work in `supabase/`.

## Migrations

- Treat committed migrations as append-only history. Do not edit, rename, or
  reorder an applied migration; add a new migration with
  `supabase migration new <descriptive_name>`.
- Keep schema, indexes, constraints, triggers, grants, RLS, and Storage policy
  changes in migrations. Do not rely on a manual dashboard or database change
  as the source of record.
- Keep [seed.sql](seed.sql) deterministic and limited to local development
  fixtures. Never add production credentials, secrets, or customer data.

## Authorization and Storage

- Enable and test RLS for every new application table exposed through the
  Data API. Use policies targeted to the intended role and ownership model.
- Ownership must be derived from `auth.uid()` and enforced by RLS. Client input
  may be convenient, but it is never the authority for a profile ID or a row
  owner.
- Updates that protect ownership need both `USING` and `WITH CHECK` conditions.
  Verify that a user cannot transfer an owned row to another user.
- Keep note attachments private. Any change to the `note-attachments` bucket,
  permitted MIME types, size limit, or object-path policy requires a migration
  and matching Storage-policy review. Upsert support requires `SELECT`,
  `INSERT`, and `UPDATE` access.
- Do not place service-role or secret keys in clients, fixtures, or committed
  configuration. Normal application access must remain constrained by the
  authenticated user session and RLS.

## Verification

- Run `supabase db reset --local` after migration or seed changes to prove the
  local schema is reproducible and the configured seed loads.
- Run `supabase test db --local` after changes to schema, ownership defaults,
  RLS, or Storage policies. Add or update pgTAP coverage for authorization
  behavior that changes.
- Run `git diff --check` before handoff. Update [README.md](README.md) and
  [ROADMAP.md](ROADMAP.md) when workflows or backend delivery status change.

## References

- [Repository entry point](../README.md)
- [Shared contributor instructions](../AGENTS.md)
- [Product baseline](../docs/product.md)
- [Repository roadmap](../ROADMAP.md)
- [Supabase component roadmap](ROADMAP.md)
