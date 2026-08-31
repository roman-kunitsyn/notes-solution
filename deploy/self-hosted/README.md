# Self-hosted Supabase deployment

This directory contains the Docker Compose deployment for the Notes Supabase
backend. It is the current supported deployment target. It does not deploy a
Notes client: the CLI runs separately, and the bot does not yet provide Notes
CRUD. Kubernetes is planned platform work, not a supported deployment target.

For the project-wide deployment boundary and platform status, read the
[deployment overview](../../docs/deployment.md). For a Linux VPS, follow the
[production deployment runbook](docs/production-deployment.md).

## Local deployment files

- `docker-compose.yml` is the base Supabase stack.
- `docker-compose.production.yml` binds the API gateway and database pooler to
  loopback and uses named database and Storage volumes.
- `docker-compose.caddy.yml` terminates HTTPS and is used with the production
  override.
- `.env` and `.env.production` hold environment-specific configuration; do not
  commit real secrets.
- `scripts/production.sh` consistently selects the three production Compose
  files. `scripts/healthcheck.sh`, `scripts/backup.sh`, and
  `scripts/restore.sh` provide the project operational procedures.

The macOS-only `docker-compose.colima.yml` is not part of the Linux production
deployment.

## Production operations

Run production commands from this directory with a prepared `.env.production`:

```sh
scripts/production.sh validate
scripts/production.sh pull
scripts/production.sh up
scripts/production.sh health
```

Use the runbook for prerequisites, secret handling, application migrations,
HTTPS verification, backups, restoration, updates, and rollback.

## Authoritative upstream references

Generic Supabase configuration, release history, and image versions are
maintained upstream rather than copied into this repository.

- [Self-hosting with Docker](https://supabase.com/docs/guides/self-hosting/docker)
  — installation, configuration, secrets, and security.
- [Update a self-hosted deployment](https://supabase.com/docs/guides/self-hosting/updating)
  — supported update procedure and breaking-change handling.
- [Self-hosted configuration reference](https://github.com/supabase/supabase/blob/master/docker/CONFIG.md)
  — environment variables.
- [Self-hosted Docker changelog](https://github.com/supabase/supabase/blob/master/docker/CHANGELOG.md)
  and [version history](https://github.com/supabase/supabase/blob/master/docker/versions.md)
  — release and image-version records.
