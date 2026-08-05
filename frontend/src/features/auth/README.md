# Authentication feature

Owns the temporary login experience and its role-oriented guidance. It calls only `api/auth.ts`; it does not access monitor state, events, or WebSocket inference. A successful `safety_manager` login hands the typed user to `App.tsx`, which opens the existing monitor baseline. Other roles remain on the temporary confirmation screen. The mock API and the contract to replace it are recorded in [`frontend/API_MOCKS.md`](../../API_MOCKS.md).
