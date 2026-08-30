# Authentication feature

Owns login, forced temporary-password replacement, and the `system_admin` account-management workspace. It calls `api/auth.ts` for account contracts and lets administrators type the responsible area ID directly; backend validation and RBAC remain authoritative. The saved monitoring-zone collection is still used to resolve assigned IDs to display names in the account table. Account rows open the selected user's role-and-permissions editor, while their password-reset action opens Security with that same user selected. A confirmed Telegram link can be disconnected from the role-and-permissions tab, clearing its stored Chat ID so future alerts no longer select that account as a recipient. The admin workspace reuses the application sidebar and provides separate tabs for account CRUD, role/area/Telegram assignment, administrator-issued password resets, and one shared active mock-camera stream. A normal user can replace a password only while `must_change_password=true`; forgotten-password recovery returns to System Admin.

After login or session restoration, `system_admin` and `safety_manager` land on Live Monitor;
only `area_manager` lands on the area dashboard. Media Library remains available to System Admin
through navigation but is never the default landing page.
