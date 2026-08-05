# Agent Guidelines & Workflow Rules

## Core Rules & Guidelines

- **Documentation Navigation**: Refer to [`docs/README.md`](docs/README.md) as the master index to understand what documentation exists, what it contains, and when to read or update each file.
- **Project Overview**: Read `README.md` to understand the high-level project overview and quick start guide.
- **Current Project Structure**: Read [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) to understand the filesystem that currently exists. Every time you complete tasks that change project structure (creating new files/directories or updating existing layout), update `docs/PROJECT_STRUCTURE.md`.
- **Approved Target Structure (Mandatory, Read-Only)**: Before creating or modifying production code, read [`docs/FUTURE_PROJECT_STRUCTURE.md`](docs/FUTURE_PROJECT_STRUCTURE.md) completely and use it to determine the primary owning module, allowed dependencies, public contracts, test layer, and incremental migration direction. **Never edit, rename, delete, move, regenerate, or overwrite this file.** If the requested work appears to require changing this target structure, stop the structural change, explain the conflict to the user, and request an explicit architecture decision; record proposals elsewhere only when the user asks.
- **Architecture**: For architecture, read `ARCHITECTURE.md` and [`docs/architecture_diagram.md`](docs/architecture_diagram.md).
- **Module Documentation**: Any created folder/module must have a `README.md` file explaining what it does. Before reading code files inside a module, read its `README.md` first.
- **Scope Alignment**: We are in the MVP phase; scope is defined in [`specs/PRD.md`](specs/PRD.md). If a request is out of scope, ask questions for clarification.
- **Central Tracking**: The repository has exactly one root [`DECISIONS.md`](DECISIONS.md) and one root [`PROGRESS.md`](PROGRESS.md). Record every module's decisions and progress there using an owning-area label such as `[Backend]`, `[Frontend]`, `[Vision]`, or `[Cross-cutting]`. Do not create module-level `DECISIONS.md` or `PROGRESS.md` files.
- **Dont read `src` folder when im not directly ask for it. **

### Target Structure Compliance

When implementing code, agents must interpret `docs/FUTURE_PROJECT_STRUCTURE.md` as an enforceable routing and ownership policy, not as a request to scaffold the entire target tree:

1. Map the requested task or user story to exactly one primary owning module before editing code.
2. Read the owning module's `README.md` before reading or modifying implementation files inside it.
3. Create only the files and directories required by the current task; migrate only the code touched by that task.
4. Follow the documented dependency direction and communicate across module boundaries only through public services, ports, or versioned contracts.
5. Do not import another module's internal ORM models or repositories, and do not use generic `common`, `utils`, `helpers`, or `shared` locations to avoid assigning ownership.
6. Any created folder/module must include its required `README.md`, tests must live in the documented test layer, and the actual filesystem change must be reflected in `docs/PROJECT_STRUCTURE.md`.
7. If no single owner can be identified, or the task requires a new top-level directory or an unapproved module, do not invent a boundary. Report the ambiguity and request a decision from the user.
8. Existing code outside the target layout is not permission for a broad refactor. Preserve current contracts and migrate incrementally unless the user explicitly scopes a larger migration.

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
