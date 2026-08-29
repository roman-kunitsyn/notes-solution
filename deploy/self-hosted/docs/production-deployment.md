# Production Deployment Runbook

This runbook deploys the self-hosted Supabase stack to a Linux VPS.

It assumes:

- a fresh Linux VPS;
- a domain name;
- Docker Engine with Docker Compose;
- Git, curl, jq, psql and Supabase CLI;
- ports 80 and 443 available;
- production secrets prepared locally.

## Deployment files

Production uses:

- `docker-compose.yml`
- `docker-compose.production.yml`
- `docker-compose.caddy.yml`
- `.env.production`
- `scripts/production.sh`
- `scripts/healthcheck.sh`
- `scripts/backup.sh`
- `scripts/restore.sh`

The macOS-only `docker-compose.colima.yml` must not be used.

## Required server resources

Minimum:

- 2 CPU cores
- 4 GB RAM
- 40 GB SSD

Recommended:

- 4 CPU cores
- 8 GB RAM
- 80 GB SSD

Storage requirements must include database data, uploaded files, Docker images,
logs and temporary backup archives.

## Required DNS

Create an `A` record:

```text
api.example.com → VPS public IPv4 address
```

If IPv6 is configured, also create an `AAAA` record.

Do not start Caddy until DNS resolves to the VPS.

## Required firewall access

Publicly accessible:

- TCP 22: SSH, preferably restricted by source IP
- TCP 80: HTTP and certificate validation
- TCP 443: HTTPS

Not publicly accessible:

- TCP 5432: PostgreSQL session pooler
- TCP 6543: PostgreSQL transaction pooler
- TCP 8000: Envoy API gateway

The Compose configuration binds ports 5432, 6543 and 8000 to `127.0.0.1`.

## Production secrets

The server requires `.env.production`.

This file:

- must not be committed to Git;
- must have permissions `600`;
- must be transferred over an encrypted channel;
- must be stored in an encrypted password or secrets manager;
- must be included in encrypted disaster-recovery documentation.

Verify:

```sh
chmod 600 .env.production
git check-ignore .env.production
```

Never reuse development secrets in production.

## Configure production URLs

Replace placeholders in `.env.production`:

```dotenv
PROXY_DOMAIN=api.example.com
SUPABASE_PUBLIC_URL=https://api.example.com
API_EXTERNAL_URL=https://api.example.com/auth/v1
SITE_URL=https://app.example.com
ADDITIONAL_REDIRECT_URLS=https://app.example.com/**
```

## Configure SMTP

Set:

```dotenv
SMTP_ADMIN_EMAIL=admin@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=replace-with-real-user
SMTP_PASS=replace-with-real-password
SMTP_SENDER_NAME=Personal Supabase

ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false
```

Configure SPF, DKIM and DMARC records according to the selected email provider.

## Preflight validation

Run:

```sh
scripts/production.sh validate
scripts/production.sh validate-https
```

Both commands must pass before deployment.

Inspect the resolved configuration:

```sh
scripts/production.sh config > /tmp/production-compose.yml
```

Confirm that no PostgreSQL or Envoy port binds to `0.0.0.0`.

## Initial deployment

Pull pinned images:

```sh
scripts/production.sh pull
```

Start the deployment:

```sh
scripts/production.sh up
```

Inspect status:

```sh
scripts/production.sh ps
```

Inspect failing services individually:

```sh
scripts/production.sh logs auth
scripts/production.sh logs db
scripts/production.sh logs storage
scripts/production.sh logs api-gw
```

## Apply application migrations

Build the local database connection through the session pooler:

```sh
POOLER_TENANT_ID="$(
  sed -n 's/^POOLER_TENANT_ID=//p' .env.production
)"

POSTGRES_PASSWORD="$(
  sed -n 's/^POSTGRES_PASSWORD=//p' .env.production
)"

PRODUCTION_DB_URL="postgresql://postgres.${POOLER_TENANT_ID}:${POSTGRES_PASSWORD}@127.0.0.1:5432/postgres?sslmode=disable"
```

Preview migrations:

```sh
supabase db push \
  --dry-run \
  --db-url "$PRODUCTION_DB_URL"
```

Apply only after reviewing the preview:

```sh
supabase db push \
  --db-url "$PRODUCTION_DB_URL"
```

Verify:

```sh
supabase migration list \
  --db-url "$PRODUCTION_DB_URL"

supabase db advisors \
  --db-url "$PRODUCTION_DB_URL"
```

Clear credentials:

```sh
unset POSTGRES_PASSWORD
unset POOLER_TENANT_ID
unset PRODUCTION_DB_URL
```

## Verify HTTPS

```sh
curl -I https://api.example.com/auth/v1/
```

A `401` response without an API key confirms that HTTPS and gateway enforcement work.

Run the complete health check:

```sh
scripts/production.sh health
```

## Verify application security

Create two test users and confirm:

1. each user can create and read their own notes;
2. neither user can read or modify the other user's notes;
3. anonymous requests cannot read notes;
4. each user can upload and download attachments for their own notes;
5. cross-user Storage access is denied.

Never use the secret or service-role key for RLS verification.

## Verify email

Test:

1. signup confirmation;
2. password recovery;
3. email-change confirmation;
4. links use the HTTPS production domain;
5. redirects return to an allowed application URL.

## Initial backup

After deployment and verification:

```sh
BACKUP_ROOT=/var/backups/personal-supabase \
  scripts/backup.sh
```

Copy the resulting backup off the VPS and verify its checksums.

## Updating

Before every update:

1. read the Supabase self-hosted changelog;
2. create and copy an off-server backup;
3. review image and configuration changes;
4. test the update locally;
5. schedule a maintenance window.

Never use unpinned `latest` image tags.

## Rollback

Application schema rollback should use a new forward migration whenever possible.

Container rollback:

1. restore the previous pinned image tags;
2. recreate affected services;
3. run health checks.

Disaster recovery:

1. prepare a fresh initialized deployment;
2. create a fresh empty Storage volume;
3. run `scripts/restore.sh`;
4. start the target stack;
5. verify Auth, REST, RLS and Storage through their public APIs.

## Deployment completion criteria

Production is ready only when:

- all containers are healthy;
- HTTPS is valid;
- PostgreSQL is not publicly exposed;
- production secrets are independent from development;
- email confirmation works;
- migrations are current;
- RLS isolation passes;
- private Storage isolation passes;
- a backup exists outside the VPS;
- restore instructions have been rehearsed;
- health checks pass.
