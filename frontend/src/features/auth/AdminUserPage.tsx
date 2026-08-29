import {memo, useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode} from "react";
import {QRCodeSVG} from "qrcode.react";
import {changePassword, completeTelegramLink, createUser, deleteUser, listUsers, startTelegramLink, updateUserRole} from "../../api/auth";
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
  const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); onError("");
    try { const user = await createUser({full_name: fullName, email, password, role, managed_area_id: role === "area_manager" ? managedAreaId : null}); setFullName(""); setEmail(""); setPassword(""); setManagedAreaId(""); await onCreated(user); }
    catch (reason) { onError(errorMessage(reason)); } finally { setSaving(false); }
  }
  return <div className="admin-account-grid">
    <article className="admin-card"><div className="admin-card-title"><div><h3>Danh sách tài khoản</h3><p>Tìm kiếm, lọc và xóa tài khoản.</p></div><div className="admin-filters"><input aria-label="Tìm tài khoản" placeholder="Tên hoặc email" value={query} onChange={event => onQuery(event.target.value)} /><select aria-label="Lọc vai trò" value={filterRole} onChange={event => onFilterRole(event.target.value as UserRole | "")}><option value="">Tất cả vai trò</option>{roleOptions()}</select></div></div>
      <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Tài khoản</th><th>Vai trò</th><th>Khu vực & Telegram</th><th>Trạng thái</th><th /></tr></thead><tbody>{loading ? <tr><td colSpan={5}>Đang tải...</td></tr> : users.map(user => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td><span className="role-pill">{ROLE_LABELS[user.role]}</span></td><td><strong>{user.managed_area_id ? areaLabel(areas, user.managed_area_id) : "—"}</strong><small>{user.telegram_username || "Chưa liên kết Telegram"}</small></td><td><span className={user.is_active ? "status-active" : "status-inactive"}>{user.is_active ? "Hoạt động" : "Đã khóa"}</span></td><td><button className="danger-link" disabled={user.id === currentUserId} onClick={() => void onDelete(user)}>Xóa</button></td></tr>)}</tbody></table></div>
    </article>
    <article className="admin-card"><h3>Tạo tài khoản</h3><p>Cấp tài khoản và khu vực phụ trách. Telegram liên kết sau khi tạo.</p><form className="admin-form" onSubmit={submit}><label>Họ và tên<input value={fullName} onChange={event => setFullName(event.target.value)} required /></label><label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} required /></label><label>Mật khẩu tạm<input type="password" minLength={8} value={password} onChange={event => setPassword(event.target.value)} required /></label><label>Vai trò<select value={role} onChange={event => setRole(event.target.value as AssignableUserRole)}>{roleOptions()}</select></label>{role === "area_manager" && <AreaSelect areas={areas} value={managedAreaId} onChange={setManagedAreaId} />}<button className="admin-primary" disabled={saving || (role === "area_manager" && !managedAreaId)}>{saving ? "Đang tạo..." : "Tạo tài khoản"}</button></form></article>
  </div>;
}

function RoleTab({areas, users, selected, onSelect, onUpdated, onError}: {areas: MonitoringZone[]; users: ManagedUser[]; selected?: ManagedUser; onSelect: (id: string) => void; onUpdated: (user: ManagedUser) => Promise<void>; onError: (message: string) => void;}) {
  const [role, setRole] = useState<AssignableUserRole>(selected?.role ?? "safety_manager");
  const [managedAreaId, setManagedAreaId] = useState(selected?.managed_area_id ?? "");
  const [cameraIds, setCameraIds] = useState<string[]>(selected?.managed_camera_ids ?? []);
  const [cameraMenuOpen, setCameraMenuOpen] = useState(false);
  useEffect(() => { if (selected) { setRole(selected.role); setManagedAreaId(selected.managed_area_id ?? ""); setCameraIds(selected.managed_camera_ids ?? []); } }, [selected]);
  async function save() { if (!selected) return; onError(""); try { await onUpdated(await updateUserRole(selected.id, {role, managed_area_id: role === "area_manager" ? managedAreaId : null, managed_camera_ids: role === "area_manager" ? cameraIds : []})); } catch (reason) { onError(errorMessage(reason)); } }
  const unchanged = selected?.role === role && (selected?.managed_area_id ?? "") === (role === "area_manager" ? managedAreaId : "");
  return <AdminSelectionLayout users={users} selected={selected} onSelect={onSelect}><h3>Phân vai trò và nơi nhận cảnh báo</h3><p>Mọi thay đổi sẽ thu hồi các phiên đang hoạt động của tài khoản.</p>{selected && <div className="admin-form"><label>Vai trò mới<select value={role} onChange={event => setRole(event.target.value as AssignableUserRole)}>{roleOptions()}</select></label>{role === "area_manager" && <><AreaSelect areas={areas} value={managedAreaId} onChange={setManagedAreaId} /><div className="camera-picker"><span>Camera phụ trách</span><button type="button" className="camera-picker-trigger" onClick={() => setCameraMenuOpen(value => !value)}><span className="camera-picker-value">{cameraIds.length ? cameraIds.map(id => <i key={id}>Cam {id.slice(-1)}</i>) : "Chọn camera"}</span><b>⌄</b></button>{cameraMenuOpen && <div className="camera-picker-menu">{["cam_1","cam_2","cam_3","cam_4"].map(id => <label key={id} className={cameraIds.includes(id) ? "checked" : ""}><input type="checkbox" checked={cameraIds.includes(id)} onChange={() => setCameraIds(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id])} /><span>Camera {id.slice(-1)}</span><em>✓</em></label>)}<button type="button" onClick={() => setCameraMenuOpen(false)}>Xong</button></div>}</div></>}<TelegramLinkControls userId={selected.id} onLinked={() => undefined} onError={onError} /><div className="permission-preview"><strong>Quyền theo vai trò</strong><span>{permissionSummary(role)}</span></div><button className="admin-primary" disabled={unchanged || (role === "area_manager" && !managedAreaId)} onClick={() => void save()}>Lưu vai trò</button></div>}</AdminSelectionLayout>;
}

function TelegramLinkControls({userId, onLinked, onError}: {userId: string; onLinked: (chatId: string, username: string | null | undefined) => void; onError: (message: string) => void;}) {
  const [link, setLink] = useState(""); const [checking, setChecking] = useState(false); const [hint, setHint] = useState(""); const [copied, setCopied] = useState(false); const [showQr, setShowQr] = useState(false);
  async function begin(mode: "qr" | "link") { try { const result = await startTelegramLink(userId); setLink(result.link_url); setShowQr(mode === "qr"); setHint(mode === "qr" ? "Quét mã hoặc mở Telegram, sau đó bấm Start trong bot." : "Đã tạo link. Sao chép link để gửi cho người cần liên kết."); } catch (reason) { onError(errorMessage(reason)); } }
  async function complete() { setChecking(true); try { const result = await completeTelegramLink(userId); if (result.status === "linked" && result.chat_id) { onLinked(result.chat_id, result.telegram_username); setHint("Đã liên kết thành công. Bấm Lưu vai trò để hoàn tất."); } else setHint(result.status === "expired" ? "Mã đã hết hạn. Hãy tạo mã mới." : "Chưa thấy tin nhắn Start. Hãy thử lại sau khi bấm Start."); } catch (reason) { onError(errorMessage(reason)); } finally { setChecking(false); } }
  async function copy() { if (!link) return; await navigator.clipboard.writeText(link); setCopied(true); window.setTimeout(() => setCopied(false), 1600); }
  return <section className="telegram-link-card"><div className="telegram-link-heading"><span className="telegram-link-icon" aria-hidden="true">✈</span><div><strong>Liên kết Telegram</strong><p>Nhận Chat ID tự động, không cần nhập thủ công.</p></div></div>{!link ? <div className="telegram-link-choice"><button type="button" className="telegram-link-create" onClick={() => void begin("qr")}>Tạo QR liên kết</button><button type="button" className="telegram-link-outline" onClick={() => void begin("link")}>Tạo link liên kết</button></div> : <div className={`telegram-link-ready ${showQr ? "" : "link-only"}`}>{showQr && <div className="telegram-qr"><QRCodeSVG value={link} size={132} bgColor="#ffffff" fgColor="#102a24" level="M" includeMargin /></div>}<div className="telegram-link-steps"><span className="telegram-badge">BƯỚC 1 / 2</span><h4>{showQr ? "Quét mã bằng điện thoại" : "Link liên kết"}</h4><p>{hint}</p>{!showQr && <code className="telegram-link-url">{link}</code>}<div className="telegram-link-actions"><a href={link} target="_blank" rel="noreferrer">Mở Telegram</a><button type="button" onClick={() => void copy()}>{copied ? "Đã sao chép" : "Sao chép link"}</button></div><button type="button" className="telegram-link-done" disabled={checking} onClick={() => void complete()}>{checking ? "Đang xác minh..." : "Tôi đã bấm Start"}</button><div className="telegram-link-secondary"><button type="button" className="telegram-link-reset" onClick={() => void begin(showQr ? "qr" : "link")}>{showQr ? "Tạo QR mới" : "Tạo link mới"}</button><button type="button" className="telegram-link-reset" onClick={() => { setLink(""); setHint(""); }}>← Quay lại</button></div></div></div>}</section>;
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
function areaLabel(areas: MonitoringZone[], areaId: string): string { return areas.find(area => area.zone_id === areaId)?.display_name ?? areaId; }
function permissionSummary(role: UserRole): string { return role === "system_admin" ? "Toàn quyền quản trị, giám sát, cấu hình camera và xử lý sự kiện an toàn." : role === "safety_manager" ? "Theo dõi, review và xác nhận sự kiện an toàn." : "Xem dữ liệu và báo cáo trong phạm vi khu vực."; }
function errorMessage(reason: unknown): string { return reason instanceof Error ? reason.message : "Không thể hoàn tất yêu cầu."; }
