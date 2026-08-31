# Notes

`notes-solution` is the repository for Notes, a personal notes product built on
Supabase. The Notes CLI is the functional reference client for the currently
supported product baseline.

## Supported today

- Authentication
- Notes CRUD
- Private note attachments

Tags and rich search are future capabilities. New capabilities normally
stabilize in the CLI before they propagate to other clients.

## Start here

- [Product baseline](docs/product.md)
- [Documentation index](docs/README.md)
- [Notes CLI](apps/notes-cli/README.md)
- [Notes Telegram bot](apps/notes-bot/README.md)
- [Self-hosted Supabase with Docker Compose](deploy/self-hosted/README.md)

The Telegram bot currently supports secure account linking; it does not yet
support Notes CRUD. Self-hosted Supabase is available through Docker Compose.
Kubernetes is not a current capability.
