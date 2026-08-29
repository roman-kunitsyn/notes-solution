# Changelog

All notable changes to Notes CLI are documented here.

## [0.1.0] - 2026-08-29

### Added

- Supabase connection configuration.
- Email and password authentication.
- Persistent local sessions.
- Note list, show, create, edit, and delete commands.
- Interactive editor support.
- Private attachment upload, list, download, and deletion.
- Friendly Auth, REST, Storage, and network errors.
- User-isolation enforcement through Supabase RLS.
- Unit and end-to-end integration tests.
- Ruff and pytest CI checks.

### Security

- Accepts publishable and legacy anonymous API keys.
- Rejects secret and service-role keys.
- Stores local configuration and sessions with restricted permissions.
- Never assigns note ownership from client input.
- Relies on authenticated Supabase RLS for database and Storage access.
