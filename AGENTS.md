# Agent Guidelines & Workflow Rules

## Core Rules & Guidelines

- **Documentation Navigation**: Refer to [`docs/README.md`](docs/README.md) as the master index to understand what documentation exists, what it contains, and when to read or update each file.
- **Project Overview**: Read `README.md` to understand the high-level project overview and quick start guide.
- **Project Structure**: Read [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) to understand current and future directory layouts. Every time you complete tasks that change project structure (creating new files/directories or updating existing layout), update `docs/PROJECT_STRUCTURE.md`.
- **Architecture**: For architecture, read `ARCHITECTURE.md` and [`docs/architecture_diagram.md`](docs/architecture_diagram.md).
- **Module Documentation**: Any created folder/module must have a `README.md` file explaining what it does. Before reading code files inside a module, read its `README.md` first.
- **Scope Alignment**: We are in the MVP phase; scope is defined in [`specs/PRD.md`](specs/PRD.md). If a request is out of scope, ask questions for clarification.
- **Central Tracking**: The repository has exactly one root [`DECISIONS.md`](DECISIONS.md) and one root [`PROGRESS.md`](PROGRESS.md). Record every module's decisions and progress there using an owning-area label such as `[Backend]`, `[Frontend]`, `[Vision]`, or `[Cross-cutting]`. Do not create module-level `DECISIONS.md` or `PROGRESS.md` files.
- **Dont read `src` folder when im not directly ask for it. **

---

## Session Workflow

### At Session Start (Clock In)
1. Read root `PROGRESS.md` for the project-wide current state.
2. Read root `DECISIONS.md` for important decisions across all modules.
3. Run `make check` to confirm repo is in consistent state. Skip this step if you only update documents.
4. Continue from `PROGRESS.md` `Next Steps` section.

### Before Session End (Clock Out)
1. Update root `PROGRESS.md`.
2. Run `make check` to confirm consistent state.
3. Commit all completed work (if requested directly by user).

---

## Template Examples

### `DECISIONS.md` Example

```markdown
# Design Decisions

## 2024-01-15: Use Redis for user preferences caching
- Reason: High read frequency (every API call), small data size
- Rejected alternative: PostgreSQL materialized view (high change frequency makes maintenance cost not worthwhile)
- Constraint: Cache TTL of 5 minutes, active invalidation on write
```

### `PROGRESS.md` Example

```markdown
# Project Progress

## Current State
- Latest commit: abc1234 (feat: add user preferences endpoint)
- Test status: 42/43 passing (test_pagination_edge_case failing)
- Lint: passing

## Completed
- [x] User model and database migration
- [x] Basic CRUD endpoints
- [x] Auth middleware integration

## In Progress
- [ ] Pagination feature (90% - edge case test failing)

## Known Issues
- test_pagination_edge_case returns 500 on empty result sets
- Need to confirm whether deleted users should appear in listings

## Next Steps
1. Fix pagination edge case bug
2. Add "include deleted users" query parameter
3. Update API documentation
```
