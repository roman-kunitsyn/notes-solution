# Notes product baseline

## Product and repository

**Notes** is the product name. **`notes-solution`** is the repository umbrella
for its clients, Supabase configuration, and deployment assets.

The Notes CLI is the functional reference client. New product capabilities are
delivered to the CLI first, then to other clients as they become available.

## Supported baseline

Notes currently supports:

- email-and-password authentication;
- creating, listing, viewing, editing, and deleting a user's notes; and
- private note attachments: upload, list, download, and delete.

Supabase Row Level Security protects each user's Notes data and attachments.
The attachment bucket accepts PNG, JPEG, PDF, and plain-text files up to 10
MiB.

## Not yet supported

Tags and rich search are future capabilities. The database schema includes tag
tables for later use, but the current reference client does not provide tag
commands or a rich-search workflow.

The Notes bot can create, list, and view notes for a linked account in a
private Telegram chat, but it is not yet a supported full Notes CRUD client.
Its remaining scope is edit and delete work.

## References

- [Notes CLI](../apps/notes-cli/README.md)
- [Notes bot](../apps/notes-bot/README.md)
- [Self-hosted Supabase deployment](../deploy/self-hosted/README.md)
