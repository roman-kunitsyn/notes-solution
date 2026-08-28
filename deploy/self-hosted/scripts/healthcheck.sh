#!/usr/bin/env sh

set -eu

cd "$(dirname "$0")/.."

ENV_FILE=".env.production"

SUPABASE_URL="$(
  sed -n 's/^SUPABASE_PUBLIC_URL=//p' "$ENV_FILE"
)"

if [ -z "$SUPABASE_URL" ]; then
  echo "SUPABASE_PUBLIC_URL is missing" >&2
  exit 1
fi

if printf '%s' "$SUPABASE_URL" | grep -q 'example\.com'; then
  echo "SUPABASE_PUBLIC_URL still contains a placeholder" >&2
  exit 1
fi

PUBLISHABLE_KEY="$(
  sed -n 's/^SUPABASE_PUBLISHABLE_KEY=//p' "$ENV_FILE"
)"

if [ -z "$PUBLISHABLE_KEY" ]; then
  echo "SUPABASE_PUBLISHABLE_KEY is missing" >&2
  exit 1
fi

echo "Checking containers..."

docker compose \
  --env-file "$ENV_FILE" \
  --file docker-compose.yml \
  --file docker-compose.production.yml \
  --file docker-compose.caddy.yml \
  ps

echo "Checking Auth..."

curl --fail --silent --show-error \
  "$SUPABASE_URL/auth/v1/health" \
  --header "apikey: $PUBLISHABLE_KEY" \
  >/dev/null

echo "Checking public JWKS..."

curl --fail --silent --show-error \
  "$SUPABASE_URL/auth/v1/.well-known/jwks.json" |
  jq -e '.keys | length > 0' \
    >/dev/null

echo "Checking API-key enforcement..."

STATUS="$(
  curl --silent \
    --output /dev/null \
    --write-out '%{http_code}' \
    "$SUPABASE_URL/rest/v1/"
)"

if [ "$STATUS" != "401" ]; then
  echo "Expected REST request without API key to return 401; received $STATUS" >&2
  exit 1
fi

echo "Production health check passed"

unset PUBLISHABLE_KEY
