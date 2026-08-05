# Authentication feature

Owns the temporary login experience and its role-oriented guidance. It calls only `api/auth.ts`; it does not access monitor state, events, or WebSocket inference. The mock API and the contract to replace it are recorded in [`frontend/API_MOCKS.md`](../../API_MOCKS.md).
