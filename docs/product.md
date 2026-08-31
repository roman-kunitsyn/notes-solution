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

The Notes bot is not a supported Notes CRUD client. Its current scope is
account-linking work and future-client design.

## References

- [Notes CLI](../apps/notes-cli/README.md)
- [Notes bot](../apps/notes-bot/README.md)
- [Self-hosted Supabase deployment](../deploy/self-hosted/README.md)
