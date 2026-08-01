Always read README.md for understand project overview and current/desired project structure.

Everytime you done tasks that change project structure, such as creating new files, directories, or updating existing files, you must update README.md to reflect the current project structure.

for architecture read ARCHITECTURE.md 

Any folder/ module that created should have README.md file explaining what it does. And before reading code file you should read README.md first. 


We are in mvp phrase, scope are defined in docs/PRD.md, if request is out of scope, ask questions for clarification.

At big module - such as backend, frontend, vision will have DECISIONS.md and PROGRESS.md to record decisions and progress. Make sure update it at the correct module.

## At session start (clock in)
1. Read PROGRESS.md for current state
2. Read DECISIONS.md for important decisions
3. Run make check to confirm repo is in consistent state
4. Continue from PROGRESS.md Next Steps  section

## Before session end (clock out)
1. Update PROGRESS.md
2. Run make check to confirm consistent state
3. Commit all completed work ( if requested directly by user)

example 

# Design Decisions

## 2024-01-15: Use Redis for user preferences caching
- Reason: High read frequency (every API call), small data size
- Rejected alternative: PostgreSQL materialized view (high change frequency makes maintenance cost not worthwhile)
- Constraint: Cache TTL of 5 minutes, active invalidation on write


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