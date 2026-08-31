# Repository workflow

These instructions apply across the repository. Child `AGENTS.md` files add
local requirements or override these rules when necessary; they must not repeat
this shared workflow.

## Workflow

1. **Inspect** the relevant implementation, tests, documentation, and local
   instructions before changing anything.
2. **Plan** the smallest coherent change, including documentation and test
   impact.
3. **Implement** only the agreed scope; preserve existing behavior unless the
   task explicitly changes it.
4. **Validate** with the relevant component checks and `git diff --check`.
   The root `Makefile` is currently empty, so it defines no repository-wide
   command or quality gate.
5. **Report** the completed work concisely.

## Documentation and roadmap

Keep documentation accurate when behavior, setup, configuration, commands, or
architecture changes. Update the product baseline or roadmap documents when a
change affects stated capabilities, planned work, or delivery status. Do not
leave stale links or claims about unimplemented features.

## Configuration

- Runtime process environment is the application configuration source of
  truth. Keep precedence: explicit runtime environment > local `.env` values
  > documented safe code defaults. Explicit runtime values must always win.
- `.env` files are local-development conveniences, not canonical production
  configuration. Do not silently load arbitrary dotenv files in production
  applications or infrastructure.
- Never commit real credentials, tokens, private keys, passwords, connection
  strings, or generated dotenv files. Ignore local `.env` files. Commit an
  `.env.example` only when useful, with safe placeholders, required-variable
  markers, and the current supported configuration contract.
- Use stable, explicit uppercase snake-case names. Required configuration has
  no fallback: validate it at startup and fail fast with a clear error. Defaults
  are only for safe, non-secret, environment-independent operational values;
  never use a default to mask missing required configuration.
- Tests must inject their own configuration or use explicit test fixtures and
  safe test defaults. They must not depend on a developer's personal `.env`.
- Docker, Compose, CI/CD, and Kubernetes inject configuration explicitly.
  Compose may use a declared local deployment env file; do not bake
  environment-specific configuration or secrets into images. In Kubernetes,
  use ConfigMaps for non-secrets and Secrets for secrets, then provide them to
  containers as normal environment variables or mounted files when required.
- Each child project owns its configuration contract in its documentation:
  required and optional variables, purpose, safe defaults, and useful examples.
  Root documentation owns only these shared rules and must not duplicate child
  variable lists.
- When adding, removing, or renaming a variable, update validation,
  `.env.example` where applicable, child documentation, deployment wiring, and
  tests in the same coherent change. Prefer fewer operator-facing variables.

## Completion report

For completed implementation work, report:

- what changed;
- checks run and their results;
- important architectural, security, or documentation notes;
- remaining blockers or follow-up work, if any.

Also propose a `snake_case_format` commit message. Do not claim checks that
were not run.
