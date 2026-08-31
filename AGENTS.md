# Repository Agent Instructions

## Start Here

Read the root [README.md](README.md), then the canonical product baseline in
[docs/product.md](docs/product.md). Read the README and any applicable
documentation for the component being changed before proposing or making work.

## Documentation Hierarchy

Use documentation for its intended purpose, in this order when determining
current behavior:

1. Explicit user requirements for the task.
2. This file and applicable child `AGENTS.md` files for agent process.
3. `docs/product.md` for repository product behavior.
4. The affected component's README and operational documentation.
5. The existing implementation and tests, which must be inspected before
   planning changes.

Roadmaps describe intended future work, not current behavior. If sources
conflict or leave a material uncertainty, surface it with the evidence; do not
silently choose an interpretation. Ask the user when the conflict affects
scope, behavior, security, or a decision that cannot be safely inferred.

## Product Rules

The CLI is the reference client for new user-facing product capabilities.
Stabilize a capability in the CLI before propagating it to other clients,
unless the user explicitly directs otherwise.

## Development Workflow

Inspect the relevant implementation, tests, configuration, and local
instructions before planning a change. Keep changes scoped to the request;
prefer the existing patterns and dependencies, and avoid new architecture,
layers, or abstractions unless a demonstrated need requires them.

## Planning Rules

For work beyond a small, self-evident edit, state the intended scope, affected
components, assumptions, risks, and validation. Check the applicable roadmap
before planning; update it when the work changes a milestone, sequence, or
future scope. If no applicable roadmap exists, say so in the implementation
report rather than creating speculative roadmap content.

## Implementation Rules

Preserve established behavior outside the requested scope. Do not modify code,
configuration, generated files, or documentation unrelated to the change.

## Validation

Run the relevant documented checks for every affected component. Add or update
tests when behavior changes, and report the commands run and any checks that
could not be run.

## Documentation Updates

Update the canonical documentation when behavior, interfaces, configuration,
operations, or supported capability changes. Keep policy here concise; put
product behavior in product documentation, component details in component
documentation, and future sequencing in roadmaps.

## Reporting

After implementation, report the changed files, behavior, validation results,
documentation or roadmap updates, assumptions, and unresolved risks or
questions.

## Commit Message Convention

When providing a proposed commit message, use `snake_case_format`.

## Child Project Instructions

This file applies throughout the repository. Before working in a directory,
look for `AGENTS.md` files from the repository root to that directory. The
nearest child file adds project-specific instructions. Child files should not
repeat these root rules unless an explicit override is required. Surface any
contradiction between instructions or documentation instead of silently
resolving it; ask the user when it materially affects the work.
