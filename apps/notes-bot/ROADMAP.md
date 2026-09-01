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

### Note editing

The private-chat `/edit NOTE_ID` command replaces a linked user's note title
and content from the following lines. It uses the refreshed linked session and
the existing update RLS policy; SQLite does not persist note data.

### Note deletion

The private-chat `/delete NOTE_ID` command deletes a linked user's note through
the refreshed linked session. Supabase RLS restricts deletion to the note
owner; SQLite neither stores nor mirrors note data.

### Attachment listing

The private-chat `/attachments NOTE_ID` command lists private attachment
metadata for a note visible to the linked user. It uses the refreshed session
and existing Storage RLS policies, and does not download or persist attachment
contents.

### Attachment delivery

The private-chat `/download NOTE_ID FILENAME` command downloads an attachment
through the linked user's refreshed Supabase session and delivers it to
Telegram. Storage RLS remains the authorization boundary; the bot does not
persist attachment contents. Delivery is limited to the product's 10 MiB
attachment maximum, with safe user-facing messages for unavailable or failed
deliveries.

## Next

### Attachment deletion

Allow a linked user to delete one private attachment from a note in a private
chat. Keep the existing Storage RLS boundary and require an explicit command
confirmation before deletion.

## Later

### Follow later product capabilities

Consider bot support for attachment upload, tags, richer search, and other
client features only after each capability is implemented, documented, and
stable in the CLI and product baseline. Their future inclusion is not a claim
of current bot functionality.

## Related documentation

- [Repository roadmap](../../ROADMAP.md)
- [Product baseline](../../docs/product.md)
- [Notes CLI](../notes-cli/README.md)
- [CLI roadmap](../notes-cli/ROADMAP.md)
- [Supabase backend](../../supabase/README.md)
