#!/usr/bin/env sh

set -eu

cd "$(dirname "$0")/.."

ENV_FILE=".env.production"
COMPOSE_FILE="docker-compose.yml"
PRODUCTION_COMPOSE_FILE="docker-compose.production.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

command="${1:-help}"

case "$command" in
config)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    config
  ;;

validate)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    config --quiet

  if grep -Eq \
    '^(SITE_URL|API_EXTERNAL_URL|SUPABASE_PUBLIC_URL)=.*example\.com' \
    "$ENV_FILE"; then
    echo "Production URLs still contain example.com placeholders" >&2
    exit 1
  fi

  if grep -Eq \
    '^(SMTP_HOST|SMTP_USER|SMTP_PASS)=.*replace-before-deployment' \
    "$ENV_FILE"; then
    echo "SMTP configuration still contains placeholders" >&2
    exit 1
  fi

  if ! grep -q '^ENABLE_EMAIL_AUTOCONFIRM=false$' "$ENV_FILE"; then
    echo "ENABLE_EMAIL_AUTOCONFIRM must be false" >&2
    exit 1
  fi

  echo "Production configuration is valid"
  ;;

pull)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    pull
  ;;

up)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    up -d
  ;;

stop)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    stop
  ;;

restart)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    restart
  ;;

ps)
  docker compose \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    --file "$PRODUCTION_COMPOSE_FILE" \
    ps
  ;;

logs)
  service="${2:-}"

  if [ -n "$service" ]; then
    docker compose \
      --env-file "$ENV_FILE" \
      --file "$COMPOSE_FILE" \
      --file "$PRODUCTION_COMPOSE_FILE" \
      logs --tail=100 --follow "$service"
  else
    docker compose \
      --env-file "$ENV_FILE" \
      --file "$COMPOSE_FILE" \
      --file "$PRODUCTION_COMPOSE_FILE" \
      logs --tail=100 --follow
  fi
  ;;

help)
  echo "Usage: scripts/production.sh COMMAND"
  echo
  echo "Commands:"
  echo "  config    Render the resolved Compose configuration"
  echo "  validate  Validate configuration and production placeholders"
  echo "  pull      Pull pinned container images"
  echo "  up        Start the production stack"
  echo "  stop      Stop services without deleting data"
  echo "  restart   Restart services"
  echo "  ps        Show service status"
  echo "  logs      Follow logs, optionally for one service"
  ;;

*)
  echo "Unknown command: $command" >&2
  echo "Run: scripts/production.sh help" >&2
  exit 1
  ;;
esac
