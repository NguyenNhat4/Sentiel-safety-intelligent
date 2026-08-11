import {useState, type FormEvent} from "react";
import {login} from "../../api/auth";
import type {AuthenticatedUser, UserRole} from "../../types";
import "./login.css";

interface LoginPageProps { onAuthenticated: (user: AuthenticatedUser) => void; }

const ROLE_CARDS: Array<{role: UserRole; title: string; description: string; destination: string}> = [
  {role: "system_admin", title: "Quản trị hệ thống", description: "Quản lý tài khoản, vai trò và bảo mật truy cập.", destination: "Quản trị tài khoản"},
  {role: "safety_manager", title: "Cán bộ an toàn", description: "Theo dõi cảnh báo, xác minh vi phạm và xem nhật ký an toàn.", destination: "Live Monitor & nhật ký vi phạm"},
  {role: "area_manager", title: "Quản lý khu vực", description: "Theo dõi tình trạng tuân thủ và các sự kiện tại khu vực phụ trách.", destination: "Dashboard khu vực"}
];

export function LoginPage({onAuthenticated}: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setIsSubmitting(true);
    try { onAuthenticated((await login({email, password})).user); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể đăng nhập."); }
    finally { setIsSubmitting(false); }
  }

  return <main className="login-page"><section className="login-intro"><div className="login-brand"><span className="login-logo">S</span><span>Sentinel<small>Safety intelligence</small></span></div><p className="eyebrow">TRUNG TÂM GIÁM SÁT AN TOÀN</p><h1>Một điểm vào cho mọi vai trò an toàn.</h1><p>Đăng nhập để theo dõi rủi ro, quản lý khu vực hoặc quản trị quyền truy cập.</p><div className="role-cards">{ROLE_CARDS.map(card => <div className="role-card" key={card.role}><strong>{card.title}</strong><span>{card.description}</span><small>{card.destination}</small></div>)}</div></section><section className="login-panel"><form onSubmit={handleSubmit}><p className="eyebrow">CỔNG TRUY CẬP SENTINEL</p><h2>Chào mừng trở lại</h2><p className="form-intro">Sử dụng tài khoản được cấp để tiếp tục.</p><label>Email công việc<input aria-label="Email công việc" autoComplete="email" type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="name@company.com" required /></label><label>Mật khẩu<input aria-label="Mật khẩu" autoComplete="current-password" type="password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Nhập mật khẩu" required /></label><div className="login-message" aria-live="polite">{error && <p className="login-error" role="alert">{error}</p>}</div><button className="login-submit" disabled={isSubmitting} type="submit">{isSubmitting ? "Đang xác thực..." : "Đăng nhập"}</button></form></section></main>;
}
