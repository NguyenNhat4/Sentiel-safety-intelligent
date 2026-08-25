import {memo, useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode} from "react";
import {changePassword, createUser, deleteUser, listUsers, updateUserRole} from "../../api/auth";
import {loadMonitoringZones} from "../../api/monitoring-zones";
import type {AssignableUserRole, AuthenticatedUser, ManagedUser, MonitoringZone, UserRole} from "../../types";
import "./admin-user.css";

interface AdminUserPageProps { currentUser: AuthenticatedUser; active?: boolean; onLogout: () => void; }
type AdminTab = "accounts" | "roles" | "security";

const ROLE_LABELS: Record<UserRole, string> = {
  system_admin: "Quản trị hệ thống",
  safety_manager: "Cán bộ an toàn",
  area_manager: "Quản lý khu vực"
};

let adminUsersCache: ManagedUser[] | null = null;
let adminAreasCache: MonitoringZone[] | null = null;

export const AdminUserPage = memo(function AdminUserPage({currentUser, active = true, onLogout}: AdminUserPageProps) {
  const [tab, setTab] = useState<AdminTab>("accounts");
  const [users, setUsers] = useState<ManagedUser[]>(() => adminUsersCache ?? []);
  const [selectedId, setSelectedId] = useState(currentUser.id);
  const [query, setQuery] = useState("");
  const [filterRole, setFilterRole] = useState<UserRole | "">("");
  const [loading, setLoading] = useState(() => adminUsersCache === null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [areas, setAreas] = useState<MonitoringZone[]>(() => adminAreasCache ?? []);
  const selected = useMemo(() => users.find(user => user.id === selectedId) ?? users[0], [users, selectedId]);

  const load = useCallback(async () => {
    if (!adminUsersCache) setLoading(true);
    setError("");
    try {
      const result = await listUsers(query, filterRole);
      adminUsersCache = result;
      setUsers(result);
      setSelectedId(current => result.some(user => user.id === current) ? current : result[0]?.id ?? "");
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setLoading(false); }
  }, [query, filterRole]);

  useEffect(() => {
    if (active) void load();
  }, [active, load]);

  useEffect(() => {
    if (active) {
      loadMonitoringZones("uploaded_video")
        .then(collection => {
          adminAreasCache = collection.zones;
          setAreas(collection.zones);
        })
        .catch(reason => setError(errorMessage(reason)));
    }
  }, [active]);

  async function remove(user: ManagedUser) {
    if (!window.confirm(`Xóa tài khoản ${user.email}? Hành động này không thể hoàn tác.`)) return;
    setError(""); setMessage("");
    try { await deleteUser(user.id); setMessage(`Đã xóa ${user.email}.`); await load(); }
    catch (reason) { setError(errorMessage(reason)); }
  }

  return <section className={`page admin-page ${active ? "active" : ""}`}>
    <div className="admin-heading">
      <p>Quản lý tài khoản, vai trò và thông tin xác thực tập trung.</p>
      <div className="admin-summary"><strong>{users.length}</strong><span>tài khoản</span></div>
    </div>
    <div className="admin-tabs" role="tablist">
      <TabButton active={tab === "accounts"} onClick={() => setTab("accounts")}>Tài khoản</TabButton>
      <TabButton active={tab === "roles"} onClick={() => setTab("roles")}>Vai trò & quyền</TabButton>
      <TabButton active={tab === "security"} onClick={() => setTab("security")}>Bảo mật</TabButton>
    </div>
    {(error || message) && <div className={`admin-feedback ${error ? "error" : "success"}`} role={error ? "alert" : "status"}>{error || message}</div>}
    {tab === "accounts" && <AccountsTab areas={areas} users={users} loading={loading} currentUserId={currentUser.id} query={query} filterRole={filterRole} onQuery={setQuery} onFilterRole={setFilterRole} onCreated={async user => { setMessage(`Đã tạo ${user.email}.`); setSelectedId(user.id); await load(); }} onDelete={remove} onError={setError} />}
    {tab === "roles" && <RoleTab areas={areas} users={users} selected={selected} onSelect={setSelectedId} onUpdated={async user => { setMessage(`Đã cập nhật vai trò cho ${user.email}.`); await load(); }} onError={setError} />}
    {tab === "security" && <SecurityTab users={users} selected={selected} currentUser={currentUser} onSelect={setSelectedId} onChanged={async user => { if (user.id === currentUser.id) { await onLogout(); return; } setMessage(`Đã cấp mật khẩu tạm cho ${user.email}. Người dùng phải đổi mật khẩu ở lần đăng nhập tiếp theo.`); }} onError={setError} />}
  </section>;
});

function AccountsTab({areas, users, loading, currentUserId, query, filterRole, onQuery, onFilterRole, onCreated, onDelete, onError}: {
  areas: MonitoringZone[];
  users: ManagedUser[]; loading: boolean; currentUserId: string; query: string; filterRole: UserRole | "";
  onQuery: (value: string) => void; onFilterRole: (value: UserRole | "") => void;
  onCreated: (user: ManagedUser) => Promise<void>; onDelete: (user: ManagedUser) => Promise<void>; onError: (message: string) => void;
}) {
  const [fullName, setFullName] = useState(""); const [email, setEmail] = useState("");
  const [password, setPassword] = useState(""); const [role, setRole] = useState<AssignableUserRole>("safety_manager");
  const [managedAreaId, setManagedAreaId] = useState("");
  const [telegramUsername, setTelegramUsername] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); onError("");
    try { const user = await createUser({full_name: fullName, email, password, role, managed_area_id: role === "area_manager" ? managedAreaId : null, telegram_username: telegramUsername || null, telegram_chat_id: telegramChatId || null}); setFullName(""); setEmail(""); setPassword(""); setManagedAreaId(""); setTelegramUsername(""); setTelegramChatId(""); await onCreated(user); }
    catch (reason) { onError(errorMessage(reason)); } finally { setSaving(false); }
  }
  return <div className="admin-account-grid">
    <article className="admin-card"><div className="admin-card-title"><div><h3>Danh sách tài khoản</h3><p>Tìm kiếm, lọc và xóa tài khoản.</p></div><div className="admin-filters"><input aria-label="Tìm tài khoản" placeholder="Tên hoặc email" value={query} onChange={event => onQuery(event.target.value)} /><select aria-label="Lọc vai trò" value={filterRole} onChange={event => onFilterRole(event.target.value as UserRole | "")}><option value="">Tất cả vai trò</option>{roleOptions()}</select></div></div>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Tài khoản</th><th>Vai trò</th><th>Khu vực & Telegram</th><th>Trạng thái</th><th /></tr></thead><tbody>{loading ? <tr><td colSpan={5}>Đang tải...</td></tr> : users.map(user => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td><span className="role-pill">{ROLE_LABELS[user.role]}</span></td><td><strong>{user.managed_area_id ? areaLabel(areas, user.managed_area_id) : "—"}</strong><small>{user.telegram_username || "Chưa liên kết Telegram"}</small></td><td><span className={user.is_active ? "status-active" : "status-inactive"}>{user.is_active ? "Hoạt động" : "Đã khóa"}</span></td><td><button className="danger-link" disabled={user.id === currentUserId} onClick={() => void onDelete(user)}>Xóa</button></td></tr>)}</tbody></table></div>
    </article>
    <article className="admin-card"><h3>Tạo tài khoản</h3><p>Cấp tài khoản, khu vực phụ trách và kênh nhận cảnh báo.</p><form className="admin-form" onSubmit={submit}><label>Họ và tên<input value={fullName} onChange={event => setFullName(event.target.value)} required /></label><label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} required /></label><label>Mật khẩu tạm<input type="password" minLength={8} value={password} onChange={event => setPassword(event.target.value)} required /></label><label>Vai trò<select value={role} onChange={event => setRole(event.target.value as AssignableUserRole)}>{roleOptions()}</select></label>{role === "area_manager" && <AreaSelect areas={areas} value={managedAreaId} onChange={setManagedAreaId} />}<TelegramFields username={telegramUsername} chatId={telegramChatId} onUsername={setTelegramUsername} onChatId={setTelegramChatId} /><button className="admin-primary" disabled={saving || (role === "area_manager" && !managedAreaId)}>{saving ? "Đang tạo..." : "Tạo tài khoản"}</button></form></article>
  </div>;
}

function RoleTab({areas, users, selected, onSelect, onUpdated, onError}: {areas: MonitoringZone[]; users: ManagedUser[]; selected?: ManagedUser; onSelect: (id: string) => void; onUpdated: (user: ManagedUser) => Promise<void>; onError: (message: string) => void;}) {
  const [role, setRole] = useState<AssignableUserRole>(selected?.role ?? "safety_manager");
  const [managedAreaId, setManagedAreaId] = useState(selected?.managed_area_id ?? "");
  const [telegramUsername, setTelegramUsername] = useState(selected?.telegram_username ?? "");
  const [telegramChatId, setTelegramChatId] = useState(selected?.telegram_chat_id ?? "");
  useEffect(() => { if (selected) { setRole(selected.role); setManagedAreaId(selected.managed_area_id ?? ""); setTelegramUsername(selected.telegram_username ?? ""); setTelegramChatId(selected.telegram_chat_id ?? ""); } }, [selected]);
  async function save() { if (!selected) return; onError(""); try { await onUpdated(await updateUserRole(selected.id, {role, managed_area_id: role === "area_manager" ? managedAreaId : null, telegram_username: telegramUsername || null, telegram_chat_id: telegramChatId || null})); } catch (reason) { onError(errorMessage(reason)); } }
  const unchanged = selected?.role === role && (selected?.managed_area_id ?? "") === (role === "area_manager" ? managedAreaId : "") && (selected?.telegram_username ?? "") === telegramUsername && (selected?.telegram_chat_id ?? "") === telegramChatId;
  return <AdminSelectionLayout users={users} selected={selected} onSelect={onSelect}><h3>Phân vai trò và nơi nhận cảnh báo</h3><p>Mọi thay đổi sẽ thu hồi các phiên đang hoạt động của tài khoản.</p>{selected && <div className="admin-form"><label>Vai trò mới<select value={role} onChange={event => setRole(event.target.value as AssignableUserRole)}>{roleOptions()}</select></label>{role === "area_manager" && <AreaSelect areas={areas} value={managedAreaId} onChange={setManagedAreaId} />}<TelegramFields username={telegramUsername} chatId={telegramChatId} onUsername={setTelegramUsername} onChatId={setTelegramChatId} /><div className="permission-preview"><strong>Quyền theo vai trò</strong><span>{permissionSummary(role)}</span></div><button className="admin-primary" disabled={unchanged || (role === "area_manager" && !managedAreaId)} onClick={() => void save()}>Lưu vai trò</button></div>}</AdminSelectionLayout>;
}

function SecurityTab({users, selected, currentUser, onSelect, onChanged, onError}: {users: ManagedUser[]; selected?: ManagedUser; currentUser: AuthenticatedUser; onSelect: (id: string) => void; onChanged: (user: AuthenticatedUser) => Promise<void>; onError: (message: string) => void;}) {
  const [newPassword, setNewPassword] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!selected) return; onError(""); try { const user = await changePassword(selected.id, {new_password: newPassword}); setNewPassword(""); await onChanged(user); } catch (reason) { onError(errorMessage(reason)); } }
  return <AdminSelectionLayout users={users} selected={selected} onSelect={onSelect}><h3>Cấp lại mật khẩu tạm</h3><p>Thao tác này thu hồi toàn bộ phiên hiện tại. Người dùng phải thay mật khẩu tạm ở lần đăng nhập tiếp theo.</p>{selected?.id === currentUser.id ? <p>System Admin không thể tự cấp lại mật khẩu. Hãy nhờ một System Admin khác thực hiện khi cần khôi phục tài khoản.</p> : selected && <form className="admin-form" onSubmit={submit}><label>Mật khẩu tạm mới<input type="password" minLength={8} value={newPassword} onChange={event => setNewPassword(event.target.value)} required /></label><button className="admin-primary">Cấp mật khẩu tạm</button></form>}</AdminSelectionLayout>;
}

function AdminSelectionLayout({users, selected, onSelect, children}: {users: ManagedUser[]; selected?: ManagedUser; onSelect: (id: string) => void; children: ReactNode;}) { return <div className="admin-selection-grid"><aside className="admin-user-list">{users.map(user => <button className={selected?.id === user.id ? "selected" : ""} key={user.id} onClick={() => onSelect(user.id)}><strong>{user.full_name}</strong><small>{user.email}</small><span>{ROLE_LABELS[user.role]}</span></button>)}</aside><article className="admin-card admin-editor">{children}</article></div>; }
function TabButton({active, onClick, children}: {active: boolean; onClick: () => void; children: ReactNode;}) { return <button className={active ? "active" : ""} role="tab" aria-selected={active} onClick={onClick}>{children}</button>; }
function roleOptions() { return (Object.entries(ROLE_LABELS) as Array<[UserRole, string]>).map(([value, label]) => <option key={value} value={value}>{label}</option>); }
function AreaSelect({areas, value, onChange}: {areas: MonitoringZone[]; value: string; onChange: (value: string) => void;}) { return <label>Khu vực phụ trách<select value={value} onChange={event => onChange(event.target.value)} required><option value="">Chọn khu vực</option>{areas.map(area => <option value={area.zone_id} key={area.zone_id}>{area.display_name} ({area.zone_id})</option>)}</select></label>; }
function TelegramFields({username, chatId, onUsername, onChatId}: {username: string; chatId: string; onUsername: (value: string) => void; onChatId: (value: string) => void;}) { return <><label>Telegram username<input value={username} onChange={event => onUsername(event.target.value)} placeholder="@nguyenvana" pattern="@[A-Za-z0-9_]{5,32}" /></label><label>Telegram chat ID<input value={chatId} onChange={event => onChatId(event.target.value)} placeholder="Ví dụ: 123456789" inputMode="numeric" pattern="-?[0-9]+" /><small>Người nhận phải nhắn /start cho bot trước. Chat ID mới là địa chỉ dùng để gửi cảnh báo.</small></label></>; }
function areaLabel(areas: MonitoringZone[], areaId: string): string { return areas.find(area => area.zone_id === areaId)?.display_name ?? areaId; }
function permissionSummary(role: UserRole): string { return role === "system_admin" ? "Quản lý tài khoản, vai trò và bảo mật hệ thống." : role === "safety_manager" ? "Theo dõi, review và xác nhận sự kiện an toàn." : "Xem dữ liệu và báo cáo trong phạm vi khu vực."; }
function errorMessage(reason: unknown): string { return reason instanceof Error ? reason.message : "Không thể hoàn tất yêu cầu."; }
