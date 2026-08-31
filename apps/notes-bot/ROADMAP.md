# Notes bot roadmap

This roadmap describes planned work for the Telegram client. It does not
change the supported product baseline or the CLI contract.

## Completed

### Account linking

The bot can start from Telegram, link an existing Supabase account through a
browser email-OTP flow, persist encrypted linked sessions in local SQLite, and
serve a health endpoint.

### Recent note listing

The private-chat `/notes` command uses a refreshed linked session to list the
20 most recently updated notes permitted by Supabase RLS. SQLite remains
limited to link challenges and encrypted linked sessions.

### Note viewing

The private-chat `/note NOTE_ID` command uses a refreshed linked session to
view one note permitted by Supabase RLS. The bot does not persist or mirror
note content locally.

### Note creation

The private-chat `/create TITLE` command creates an RLS-protected note for the
linked user, with optional content on following lines. The bot sends only the
title and content to Supabase; ownership remains derived from the authenticated
session rather than from client input.

## Next

### Remaining Notes CRUD derived from the stable CLI contract

Deliver the corresponding bot operations for editing and deleting a user's
notes. Match the CLI's validated capability semantics,
authentication model, and RLS-protected ownership behavior rather than
inventing a separate bot contract.

The implementation should use the linked user session and Supabase as the
system of record. It must not mirror Notes data into SQLite or introduce a
privileged backend path for normal user operations.

## Later

### Follow later product capabilities

Consider bot support for tags, richer search, attachments, and other client
features only after each capability is implemented, documented, and stable in
the CLI and product baseline. Their future inclusion is not a claim of current
bot functionality.

## Related documentation

- [Repository roadmap](../../ROADMAP.md)
- [Product baseline](../../docs/product.md)
- [Notes CLI](../notes-cli/README.md)
- [CLI roadmap](../notes-cli/ROADMAP.md)
- [Supabase backend](../../supabase/README.md)
