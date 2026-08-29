# Agent Guidelines & Workflow Rules

## Core Rules & Guidelines

- **Context Map (Mandatory)**: Root [`context-map.md`](context-map.md) is the repository's single context map and the only documentation index. Start there to identify the minimum documents required for the current task; do not discover context by following links between child documents. Other documents must remain standalone and must not link to one another. This rules file is the only exception and may link directly to mandatory workflow context.
- **Project Overview**: Read root `context-map.md` first to understand the project and select task-relevant context before opening any other project document.
- **Current Project Structure**: Read [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) to understand the filesystem that currently exists. Every time you complete tasks that change project structure (creating new files/directories or updating existing layout), update `docs/PROJECT_STRUCTURE.md`.
- **Approved Target Structure (Mandatory, Read-Only)**: Before creating or modifying production code, read [`docs/FUTURE_PROJECT_STRUCTURE.md`](docs/FUTURE_PROJECT_STRUCTURE.md) completely. It is the single guide for the primary owner and technical layer, allowed dependencies, public contracts, test layer, common placement mistakes, and incremental migration direction. **Never edit, rename, delete, move, regenerate, or overwrite `docs/FUTURE_PROJECT_STRUCTURE.md`.** If the requested work appears to require changing the approved target structure, stop the structural change, explain the conflict to the user, and request an explicit architecture decision; record proposals elsewhere only when the user asks.
- **Runtime Contracts (Mandatory)**: Before changing an API, WebSocket message, ORM model, migration, database query, retention policy, or cross-module payload, read the owning module's routes, Pydantic schemas, frontend wire types, SQLAlchemy models, Alembic migrations, and relevant tests. These executable definitions are the current source of truth. Preserve compatibility unless the task explicitly authorizes a breaking change; record approved boundary changes in root `DECISIONS.md` and cover them with focused tests.
- **Architecture**: For system boundaries, runtime flow, safety invariants, and delivery evolution, read the single root [`ARCHITECTURE.md`](ARCHITECTURE.md).
- **Module Documentation**: Any created folder/module must have a `README.md` file explaining what it does. Before reading code files inside a module, read its `README.md` first.
- **Scope Alignment**: We are in the MVP phase; scope is defined in [`specs/PRD.md`](specs/PRD.md). If a request is out of scope, ask questions for clarification.
- **Central Tracking**: The repository has exactly one root [`DECISIONS.md`](DECISIONS.md) and one root [`PROGRESS.md`](PROGRESS.md). Record every module's decisions and progress there using an owning-area label such as `[Backend]`, `[Frontend]`, `[Vision]`, or `[Cross-cutting]`. Do not create module-level `DECISIONS.md` or `PROGRESS.md` files.
- **Dont read `src` folder when im not directly ask for it. **
- **Railway Deployment Workflow**: Code is currently deployed on Railway. Never build, push, redeploy, or otherwise mutate Railway/production unless the user explicitly requests deployment in the current conversation. A code-change request alone does not authorize deployment. By default, stop after the applicable local checks/build and report that deployment was not run.

### Target Structure Compliance

When implementing code, agents must interpret `docs/FUTURE_PROJECT_STRUCTURE.md` as an enforceable routing and ownership policy, not as a request to scaffold the entire target tree:

1. Map the requested task or user story to one production owner (`backend`, `frontend`, or `vision`) and one technical layer before editing code.
2. Read the production owner's `README.md` before reading or modifying implementation files inside it.
3. Create only the files and directories required by the current task; migrate only the code touched by that task.
4. Follow the documented dependency direction and communicate across production-owner boundaries only through public services, adapters, facades, or versioned contracts.
5. Do not bypass layer direction, and do not use generic `common`, `utils`, `helpers`, or `shared` locations to avoid assigning responsibility.
6. Boundary/provider folders must include their required `README.md`, tests must live in the documented test layer, and the actual filesystem change must be reflected in `docs/PROJECT_STRUCTURE.md`.
7. If no single owner/layer can be identified, or the task requires a new top-level directory, do not invent a boundary. Report the ambiguity and request a decision from the user.
8. Existing code outside the target layout is not permission for a broad refactor. Preserve current contracts and migrate incrementally unless the user explicitly scopes a larger migration.
9. Updated code: run the applicable local checks/build. Deploy to Railway only when the user explicitly requests deployment in the current conversation; otherwise report that deployment was not run.
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
