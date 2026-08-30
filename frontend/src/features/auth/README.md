# Authentication feature

Owns login, forced temporary-password replacement, and the `system_admin` account-management workspace. It calls `api/auth.ts` for account contracts and reads the saved monitoring-zone collection to offer valid area assignments; backend RBAC remains authoritative. The admin workspace reuses the application sidebar and provides separate tabs for account CRUD, role/area/Telegram assignment, administrator-issued password resets, and one shared active mock-camera stream. A normal user can replace a password only while `must_change_password=true`; forgotten-password recovery returns to System Admin.

After login or session restoration, `system_admin` and `safety_manager` land on Live Monitor;
only `area_manager` lands on the area dashboard. Media Library remains available to System Admin
through navigation but is never the default landing page.
