# Deployment

## Current platform status

Notes currently deploys its Supabase backend with the Docker Compose stack in
[`deploy/self-hosted/`](../deploy/self-hosted/README.md). The supported
production path is a Linux VPS using the production Compose overrides, Caddy
for TLS, and the accompanying backup, restore, and health-check scripts.

This deployment provides the Notes database, Auth, Storage, API gateway, and
Studio. It is not a complete deployment of every Notes client: the CLI runs on
the operator's machine, and the bot has no Notes CRUD deployment yet. No client
container deployment is currently provided.

## Planned platform work

Kubernetes is planned future platform work only. It is not supported, and no
Kubernetes manifests or operating procedures are maintained in this repository.
The current deployment target remains Docker Compose.

## Active deployment documentation

- [Self-hosted deployment README](../deploy/self-hosted/README.md) — local
  Compose layout, operational entry points, and upstream references.
- [Production deployment runbook](../deploy/self-hosted/docs/production-deployment.md)
  — VPS deployment, validation, backup, restore, and update procedure.
- [Supabase self-hosting documentation](https://supabase.com/docs/guides/self-hosting)
  — authoritative vendor documentation.
- [Supabase Docker self-hosting guide](https://supabase.com/docs/guides/self-hosting/docker)
  — upstream installation, configuration, and security guidance.

For the product-level sequencing of Docker Compose improvements and eventual
Kubernetes evaluation, see the [repository roadmap](../ROADMAP.md).
