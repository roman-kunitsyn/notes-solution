# Notes product baseline

<<<<<<< HEAD
Notes is a personal notes product. `notes-solution` is the repository and
project umbrella that contains its clients and Supabase-backed infrastructure.

## Supported functionality

The current supported Notes baseline is:

- Authentication
- Notes CRUD: create, list, view, edit, and delete notes
- Private attachments for notes

The [Notes CLI](../apps/notes-cli/README.md) is the functional reference
client for this baseline. It establishes the working product contract; new
capabilities should normally stabilize in the CLI before they propagate to
other clients.

## Current clients

The Telegram bot supports secure Telegram-to-Supabase account linking. It does
not yet support Notes CRUD, attachments, tags, or search.

## Future capabilities

Tags and rich search are future capabilities. Although supporting database
structures may exist, they are not currently supported Notes behavior.

## Infrastructure scope

Notes can use the self-hosted Supabase Docker Compose deployment described in
[the deployment README](../deploy/self-hosted/README.md). Kubernetes is not a
current Notes capability.
||||||| bdd41ec
=======
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

The Notes bot can create, list, view, edit, and delete notes for a linked
account in a private Telegram chat, list private attachment metadata, and
deliver a private attachment to that chat. It does not yet support attachment
upload or deletion, tags, or rich search.

## References

- [Notes CLI](../apps/notes-cli/README.md)
- [Notes bot](../apps/notes-bot/README.md)
- [Self-hosted Supabase deployment](../deploy/self-hosted/README.md)
>>>>>>> documentation
