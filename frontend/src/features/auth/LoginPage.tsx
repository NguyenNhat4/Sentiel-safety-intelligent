import {useState, type FormEvent} from "react";
import {login} from "../../api/auth";
import type {AuthenticatedUser, UserRole} from "../../types";

interface LoginPageProps {
  onAuthenticated: (user: AuthenticatedUser) => void;
}

const ROLE_CARDS: Array<{role: UserRole; title: string; description: string; destination: string}> = [
  {role: "safety_manager", title: "Quản lý an toàn", description: "Theo dõi cảnh báo, xác minh vi phạm và xem nhật ký an toàn.", destination: "Live Monitor & nhật ký vi phạm"},
  {role: "area_manager", title: "Quản lý khu vực", description: "Theo dõi tình trạng tuân thủ và các sự kiện tại khu vực phụ trách.", destination: "Dashboard khu vực"},
  {role: "simulation_operator", title: "Mô phỏng streaming", description: "Tải video lên để mô phỏng luồng camera trước khi đưa vào giám sát.", destination: "Tải video mô phỏng"}
];

export function LoginPage({onAuthenticated}: LoginPageProps) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [selectedRole, setSelectedRole] = useState<UserRole>("safety_manager"); const [user, setUser] = useState<AuthenticatedUser>(); const [error, setError] = useState(""); const [isSubmitting, setIsSubmitting] = useState(false);
  const selected = ROLE_CARDS.find((card) => card.role === selectedRole)!;
  async function handleSubmit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(""); setIsSubmitting(true); try { const result = await login({email, password}); if (result.user.role === "safety_manager") onAuthenticated(result.user); else setUser(result.user); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể đăng nhập."); } finally { setIsSubmitting(false); } }
  if (user) return <main className="login-success"><span className="login-logo">S</span><p className="eyebrow">ĐĂNG NHẬP THÀNH CÔNG</p><h1>Chào {user.full_name}</h1><p>Bạn đang vào với vai trò <strong>{user.role_label}</strong>. Màn hình <strong>{selected.destination}</strong> sẽ được kết nối ở bước tiếp theo.</p><button onClick={() => setUser(undefined)}>Quay lại đăng nhập</button></main>;
  return <main className="login-page"><section className="login-intro"><div className="login-brand"><span className="login-logo">S</span><span>Sentinel<small>Safety intelligence</small></span></div><p className="eyebrow">TRUNG TÂM GIÁM SÁT AN TOÀN</p><h1>Một điểm vào cho mọi vai trò an toàn.</h1><p>Đăng nhập để theo dõi rủi ro, quản lý khu vực hoặc chạy mô phỏng video trước khi vận hành.</p><div className="role-cards">{ROLE_CARDS.map((card) => <button className={`role-card ${selectedRole === card.role ? "selected" : ""}`} key={card.role} onClick={() => setSelectedRole(card.role)}><strong>{card.title}</strong><span>{card.description}</span><small>{card.destination}</small></button>)}</div></section><section className="login-panel"><form onSubmit={handleSubmit}><p className="eyebrow">ĐĂNG NHẬP HỆ THỐNG</p><h2>{selected.title}</h2><p className="form-intro">Sử dụng tài khoản được cấp để tiếp tục.</p><label>Email công việc<input aria-label="Email công việc" autoComplete="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.com" required /></label><label>Mật khẩu<input aria-label="Mật khẩu" autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Nhập mật khẩu" required /></label>{error && <p className="login-error" role="alert">{error}</p>}<button className="login-submit" disabled={isSubmitting} type="submit">{isSubmitting ? "Đang xác thực..." : "Đăng nhập"}</button><p className="mock-note">Bản demo đang dùng mock API. Xem tài khoản thử trong <code>frontend/API_MOCKS.md</code>.</p></form></section></main>;
}
