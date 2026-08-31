# Supabase backend roadmap

This roadmap covers backend work required by the Notes product. Product
priority remains in the [repository roadmap](../ROADMAP.md), and the supported
baseline remains in the [product documentation](../docs/product.md). It does
not define client commands, screens, or interaction design.

See the [Supabase component guide](README.md), the shared [repository
instructions](../AGENTS.md), and the [repository entry point](../README.md).

## Completed

| Date | Status | Backend outcome |
| --- | --- | --- |
| 2026-08 | Complete | Notes schema, Auth-derived ownership defaults, Data API grants, and RLS policies established. |
| 2026-08 | Complete | Private `note-attachments` Storage bucket and object policies established. |
| 2026-08 | Complete | Deterministic local seed data and pgTAP coverage for note isolation and ownership defaults established. |

## Current

### Maintain the reproducible backend baseline

**In progress.** Keep migrations, seed fixtures, and database tests aligned
with the supported Notes CRUD and private-attachment baseline. Preserve RLS as
the ownership boundary for every backend change.

## Next backend prerequisites

### Prepare a supported tag capability

**Planned.** The `tags` and `note_tags` tables already exist, but tags are not
yet a supported product capability. Before a client exposes tags, confirm the
schema and RLS contract, add coverage for tag and note-tag isolation, and
ensure migration/seed fixtures support the agreed product behavior. Client UX
is out of scope here.

### Prepare a supported search capability

**Planned.** Before clients expose search, define and test the database query,
indexing, and RLS behavior required for owned notes. Select any search
technology only after its privacy, migration, operational, and test impacts
are explicit. Client search syntax and presentation are out of scope here.

## Related documentation

- [Repository entry point](../README.md)
- [Shared contributor instructions](../AGENTS.md)
- [Product baseline](../docs/product.md)
- [Repository roadmap](../ROADMAP.md)
- [Supabase component guide](README.md)
