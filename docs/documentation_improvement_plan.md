# Executable documentation improvement plan

## Stage 1 — Establish the Notes entry point and functional baseline

**Goal:** Make the repository understandable from the root and state the current supported Notes functionality accurately.

**Inspect**

- `README.md`
- `docs/README.md`
- `apps/notes-cli/README.md`
- `apps/notes-cli/CHANGELOG.md`
- `apps/notes-bot/README.md`
- `supabase/migrations/*.sql`

**Modify / create / remove**

- Modify `README.md`
- Modify `docs/README.md`
- Create `docs/product.md`
- Remove no files

**Information movement**

- Replace the root’s stale planning prompt with a concise repository entry point.
- Make `docs/product.md` the source of truth for:
  - Notes as the product name;
  - `notes-solution` as repository umbrella;
  - CLI as functional reference client;
  - supported baseline: authentication, Notes CRUD, attachments;
  - tags and rich search as future capabilities;
  - CLI-first capability delivery, followed by other clients.
- Keep only a short product-baseline summary in root README.

**Links to add**

- Root README → `docs/product.md`, docs index, CLI README, bot README, self-hosted deployment README.
- Docs index → root README, product document, existing active component documentation.

**Contradictions resolved**

- Retire `personal-supabase` from product-facing wording.
- Remove claims that planned clients/components already exist.
- Prevent tags, rich search, and bot CRUD from appearing as currently supported.

**Validation**

- Root README describes current repository reality in under a concise entry-point scope.
- Product baseline matches CLI commands and database capabilities.
- All added relative links resolve.
- No application behavior, configuration, or source code changes.
- `git diff --check` passes.

---

## Stage 2 — Add repository-wide agent and development workflow rules

**Goal:** Give every contributor and agent one authoritative shared workflow without copying it into child projects.

**Inspect**

- Root README and docs index from Stage 1
- `apps/notes-cli/AGENTS.md`
- `apps/notes-bot/AGENTS.md`
- Existing component manifests and test commands
- Empty root `Makefile` only to document its current status, not implement it

**Modify / create / remove**

- Create `AGENTS.md`
- Create `docs/development.md`
- Modify `README.md`
- Modify `docs/README.md`
- Remove no files

**Information movement**

- Root AGENTS owns the inspect → plan → implement → validate → report workflow.
- Root AGENTS defines:
  - documentation/roadmap maintenance expectations;
  - implementation-report contents;
  - requirement to propose a `snake_case_format` commit message after completed implementation work;
  - rule that child AGENTS files add or override local rules only.
- Development docs own repository navigation and how to find component-specific setup and checks.
- Do not invent root commands while `Makefile` remains empty.

**Links to add**

- Root README → root AGENTS and development docs.
- Docs index → root AGENTS and development docs.
- Development docs → CLI, bot, Supabase, and deployment documentation entry points.

**Contradictions resolved**

- Eliminate the absence of repository-wide agent rules.
- Establish that child AGENTS files must not repeat root requirements.
- Remove any implication that an unimplemented root quality gate already exists.

**Validation**

- Root AGENTS is operational and concise.
- Development docs distinguish shared workflow from component commands.
- Links resolve and no child AGENTS files are modified yet.
- `git diff --check` passes.

---

## Stage 3 — Define architecture and product-level roadmap ownership

**Goal:** Separate current architecture from future direction and introduce a single product/repository roadmap.

**Inspect**

- `docs/product.md`
- Root README, AGENTS, docs index, development docs
- CLI and bot READMEs/AGENTS
- `supabase/config.toml`, migrations, tests
- Self-hosted deployment runbook

**Modify / create / remove**

- Create `docs/architecture.md`
- Create `ROADMAP.md`
- Modify `README.md`
- Modify `docs/README.md`
- Remove no files

**Information movement**

- Architecture owns current boundaries: Supabase as system of record, Auth/RLS/Storage, direct client access, and independently runnable clients.
- Roadmap owns product milestones and cross-component order:
  1. maintain/stabilize supported CLI behavior;
  2. implement equivalent Notes CRUD in the bot;
  3. progress container infrastructure in parallel;
  4. treat Kubernetes as future work only.
- Completed milestones use concise outcomes and dates/status—not changelog-style detail.

**Links to add**

- Root README → architecture and roadmap.
- Architecture → product, Supabase docs, deployment docs.
- Root roadmap → product docs, CLI roadmap placeholder destination, bot roadmap placeholder destination, deployment docs.

**Contradictions resolved**

- Distinguish current Docker Compose deployment from planned Kubernetes.
- Establish bot CRUD as the next client milestone after CLI stabilization.
- Prevent a future FastAPI service from being documented as a mandatory current layer.

**Validation**

- Architecture contains no hypothetical implementation detail.
- Roadmap has a clear current/next/later status model.
- No root document duplicates CLI command syntax or database migration instructions.
- `git diff --check` passes.

---

## Stage 4 — Document the Supabase component as the backend of record

**Goal:** Make database, RLS, Storage, migration, and test workflows discoverable without duplicating architecture or product policy.

**Inspect**

- `supabase/config.toml`
- `supabase/migrations/*.sql`
- `supabase/seed.sql`
- `supabase/tests/database/*.sql`
- Root AGENTS, architecture, development docs, and roadmap
- CLI security documentation

**Modify / create / remove**

- Create `supabase/README.md`
- Create `supabase/AGENTS.md`
- Create `supabase/ROADMAP.md`
- Modify `docs/README.md`
- Modify `docs/architecture.md`
- Modify `docs/development.md`
- Remove no files

**Information movement**

- Supabase README owns local lifecycle, migrations, seeds, database tests, and references to schema/security sources.
- Supabase AGENTS owns database-specific rules: migration discipline, RLS expectations, Storage policy changes, and verification requirements.
- Supabase roadmap owns backend stages needed for product milestones, including prerequisites for future tags/search—not their client UX.
- Root documents retain cross-project rules and product priority.

**Links to add**

- Supabase README/AGENTS/roadmap → root README, root AGENTS, product docs, root roadmap.
- Root architecture/development/docs index → Supabase README.

**Contradictions resolved**

- Clarify that tags exist in the schema but are not part of the current supported Notes baseline.
- Clarify that database ownership/security derives from RLS and `auth.uid()`, not client-supplied ownership identifiers.

**Validation**

- Every local Supabase workflow is traceable to a real config, migration, or test.
- No database documentation claims Kubernetes or a mandatory API service exists.
- Links resolve and `git diff --check` passes.

---

## Stage 5 — Normalize the CLI as the supported reference client

**Goal:** Keep CLI documentation factual and concise while preserving its future implementation sequence in a dedicated roadmap.

**Inspect**

- `apps/notes-cli/README.md`
- `apps/notes-cli/AGENTS.md`
- `apps/notes-cli/CHANGELOG.md`
- `apps/notes-cli/docs/README.md`
- CLI source and tests
- Root product docs, AGENTS, development docs, and roadmap

**Modify / create / remove**

- Modify `apps/notes-cli/README.md`
- Modify `apps/notes-cli/AGENTS.md`
- Modify `apps/notes-cli/CHANGELOG.md` only if navigation needs updating
- Create `apps/notes-cli/ROADMAP.md`
- Remove `apps/notes-cli/docs/README.md`
- Remove the now-empty `apps/notes-cli/docs/` directory if empty

**Information movement**

- README retains current installation, configuration, command use, supported baseline, security model, and checks.
- CLI roadmap receives only useful remaining implementation stages extracted from the old design document.
- Remove or defer speculative design detail that is neither current behavior nor a concrete roadmap milestone.
- CLI AGENTS retains only CLI-specific architecture/security/validation additions; root rules are linked, not copied.
- Changelog remains release history only.

**Links to add**

- CLI README → root README, product docs, CLI roadmap, root development docs.
- CLI AGENTS → root AGENTS and CLI roadmap.
- CLI roadmap → root roadmap, product docs, bot roadmap.
- Changelog → CLI README or release-navigation location if useful.

**Contradictions resolved**

- Remove documented-but-unimplemented CLI search, tags, filtering, output modes, and import/export from current behavior.
- Explicitly identify the CLI as the stable contract that other clients follow.

**Validation**

- Every documented CLI command exists and matches its current interface.
- Future work appears only in the CLI roadmap.
- No duplicated repository-wide instructions remain in CLI AGENTS.
- `git diff --check` passes.

---

## Stage 6 — Normalize the bot as the next CLI-derived client

**Goal:** Separate the bot’s implemented account-linking capability from its planned Notes CRUD delivery.

**Inspect**

- `apps/notes-bot/README.md`
- `apps/notes-bot/AGENTS.md`
- `apps/notes-bot/docs/README.md`
- Bot source, tests, `.env.example`, and manifest
- Root product/architecture/development/roadmap documents
- CLI roadmap

**Modify / create / remove**

- Modify `apps/notes-bot/README.md`
- Modify `apps/notes-bot/AGENTS.md`
- Create `apps/notes-bot/ROADMAP.md`
- Remove `apps/notes-bot/docs/README.md`
- Remove the now-empty `apps/notes-bot/docs/` directory if empty

**Information movement**

- Bot README owns current functionality only: Telegram startup, account linking/email OTP, encrypted linked sessions, local SQLite state, and health endpoint.
- Bot roadmap owns future client stages, beginning with Notes CRUD derived from stable CLI behavior.
- Bot AGENTS keeps only Telegram, OTP, session, SQLite, and HTTP-security constraints.
- Extract durable security constraints from the old planning documents; discard outdated target-shape examples and unsupported functionality claims.

**Links to add**

- Bot README → root README, product docs, bot roadmap, development docs.
- Bot AGENTS → root AGENTS and bot roadmap.
- Bot roadmap → root roadmap, product docs, CLI README/roadmap, Supabase README.

**Contradictions resolved**

- Remove claims that bot CRUD, search, tags, attachments, Docker packaging, or Kubernetes behavior already exists.
- Establish the bot’s dependency on CLI-stabilized capability semantics.

**Validation**

- Bot README matches implemented handlers/services/tests.
- Bot roadmap clearly separates current account-linking completion from future Notes operations.
- AGENTS is local-only and does not restate root workflow.
- `git diff --check` passes.

---

## Stage 7 — Clarify deployment scope and archive non-authoritative material

**Goal:** Leave concise, project-specific deployment knowledge active and clearly separate historical material.

**Inspect**

- `docs/deployment.md`
- `deploy/self-hosted/README.md`
- `deploy/self-hosted/docs/production-deployment.md`
- `deploy/self-hosted/CONFIG.md`
- `deploy/self-hosted/CHANGELOG.md`
- `deploy/self-hosted/versions.md`
- `docs/_conversation/`
- Deployment scripts and Compose files
- Root docs index and roadmap

**Modify / create / remove**

- Modify `docs/deployment.md`
- Modify `deploy/self-hosted/README.md`
- Modify `deploy/self-hosted/docs/production-deployment.md`
- Modify `docs/README.md`
- Create `docs/archive/README.md`
- Move `docs/_conversation/` → `docs/archive/conversation/`
- Remove `deploy/self-hosted/CONFIG.md`, `CHANGELOG.md`, and `versions.md` after extracting any verified project-specific deviation or operational knowledge into the local README/runbook
- Remove stale links to removed vendor copies

**Information movement**

- Root deployment docs own current-vs-planned platform status and the progression toward Kubernetes.
- Self-hosted README/runbook own project-specific Docker Compose operations and upstream-reference links.
- Generic vendor configuration/changelog/version material is replaced by authoritative upstream links.
- Archive README labels conversations as historical, unmaintained, and non-authoritative.

**Links to add**

- Root deployment docs → self-hosted README/runbook and authoritative upstream self-hosted documentation.
- Self-hosted README → local runbook and upstream configuration/update/changelog sources.
- Docs index → deployment docs and archive notice.
- Archive README → active docs index.

**Contradictions resolved**

- Stop implying self-hosted Supabase documentation equals full Notes-product deployment.
- Remove local generic vendor copies as competing sources of truth.
- Mark Docker Compose as current and Kubernetes as planned only.
- Prevent historical transcripts from appearing as active documentation.

**Validation**

- All active deployment links resolve.
- Local deployment docs contain only project-specific operational knowledge.
- Archived material is discoverable but clearly non-authoritative.
- No active documentation claims Kubernetes support or client container deployment exists.
- `git diff --check` passes.
