# Notes product baseline

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
