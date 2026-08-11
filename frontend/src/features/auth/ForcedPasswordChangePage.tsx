import {useState, type FormEvent} from "react";
import {changeOwnPassword} from "../../api/auth";
import type {AuthenticatedUser} from "../../types";
import "./login.css";

export function ForcedPasswordChangePage({user, onChanged}: {
  user: AuthenticatedUser;
  onChanged: () => Promise<void>;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await changeOwnPassword({current_password: currentPassword, new_password: newPassword});
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đổi mật khẩu.");
    } finally {
      setSaving(false);
    }
  }

  return <main className="login-page">
    <section className="login-intro">
      <div className="login-brand"><span className="login-logo">S</span><span>Sentinel<small>Safety intelligence</small></span></div>
      <p className="eyebrow">BẢO MẬT TÀI KHOẢN</p>
      <h1>Đổi mật khẩu tạm trước khi tiếp tục.</h1>
      <p>Tài khoản {user.email} đang sử dụng mật khẩu do System Admin cấp. Sau khi đổi thành công, hãy đăng nhập lại bằng mật khẩu mới.</p>
    </section>
    <section className="login-panel"><form onSubmit={submit}>
      <p className="eyebrow">ĐỔI MẬT KHẨU BẮT BUỘC</p>
      <h2>Lần đăng nhập đầu tiên</h2>
      <label>Mật khẩu tạm<input aria-label="Mật khẩu tạm" type="password" autoComplete="current-password" minLength={8} value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required /></label>
      <label>Mật khẩu mới<input aria-label="Mật khẩu mới" type="password" autoComplete="new-password" minLength={8} value={newPassword} onChange={event => setNewPassword(event.target.value)} required /></label>
      {error && <p className="login-error" role="alert">{error}</p>}
      <button className="login-submit" disabled={saving}>{saving ? "Đang đổi..." : "Đổi mật khẩu"}</button>
    </form></section>
  </main>;
}
