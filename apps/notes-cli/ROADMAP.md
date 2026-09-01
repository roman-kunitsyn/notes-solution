# Notes CLI roadmap

The CLI is the stable contract that other Notes clients follow. This roadmap
contains planned CLI work only; it does not describe current supported
behavior.

## Next

### Tags, search, and filtering

Deliver tag management and backend-backed search, then extend note listing
with product-supported filters. Define and test the command interfaces only
after the corresponding product and database capabilities are ready.

### Scriptable output and navigation

Add consistent machine-readable and plain-text output modes for data-producing
commands, plus pagination where result sets need it. Preserve the current
human-readable output as the default.

## Later

### Import and export

Provide a documented, portable backup and restore format for notes and their
attachments. Define conflict handling and ownership boundaries before exposing
an import command.

### CLI polish

Improve error categories and stable exit codes, configuration defaults, and
terminal ergonomics as needs are demonstrated. Keep new behavior covered by
unit and local-Supabase integration tests.

## Deferred

Offline synchronization, a local Notes mirror, a TUI, plugins, AI features,
and multi-account support are not planned CLI milestones.

## Related documentation

- [Repository roadmap](../../ROADMAP.md)
- [Product baseline](../../docs/product.md)
- [Bot roadmap](../notes-bot/ROADMAP.md) *(planned component document)*
