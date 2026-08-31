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

## Completion report

For completed implementation work, report:

- what changed;
- checks run and their results;
- important architectural, security, or documentation notes;
- remaining blockers or follow-up work, if any.

Also propose a `snake_case_format` commit message. Do not claim checks that
were not run.
