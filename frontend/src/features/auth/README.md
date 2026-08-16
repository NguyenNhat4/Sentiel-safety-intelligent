# Authentication feature

Owns login, forced temporary-password replacement, and the `system_admin` account-management workspace. It calls only `api/auth.ts`; backend RBAC remains authoritative for account APIs. The admin workspace reuses the application sidebar and provides separate tabs for account CRUD, role assignment, and administrator-issued password resets. A normal user can replace a password only while `must_change_password=true`; forgotten-password recovery returns to System Admin.
