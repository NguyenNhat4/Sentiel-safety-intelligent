import {memo, useCallback, useEffect, useState, type FormEvent} from "react";
import {deleteMediaAsset, listMediaAssets, uploadMediaAsset} from "../../api/media-assets";
import type {MediaAsset} from "../../types";
import "./media-library.css";

interface MediaLibraryPageProps {
  active?: boolean;
}

let mediaAssetsCache: MediaAsset[] | null = null;

export const MediaLibraryPage = memo(function MediaLibraryPage({active = true}: MediaLibraryPageProps) {
  const [assets, setAssets] = useState<MediaAsset[]>(() => mediaAssetsCache ?? []);
  const [displayName, setDisplayName] = useState("");
  const [file, setFile] = useState<File>();
  const [loading, setLoading] = useState(() => mediaAssetsCache === null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const loaded = await listMediaAssets();
      mediaAssetsCache = loaded;
      setAssets(loaded);
    }
    catch (reason) { setError(errorText(reason, "Không thể tải thư viện media.")); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (active) void load();
  }, [active, load]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || saving) return;
    const fileInput = event.currentTarget.elements.namedItem("media_file") as HTMLInputElement;
    setSaving(true); setError(""); setMessage("");
    try {
      const asset = await uploadMediaAsset(displayName.trim(), file);
      setAssets(current => [asset, ...current.filter(item => item.id !== asset.id)]);
      setDisplayName(""); setFile(undefined);
      fileInput.value = "";
      setMessage("Đã tiếp nhận media. Trạng thái xử lý được cập nhật từ máy chủ.");
    } catch (reason) { setError(errorText(reason, "Không thể tải media lên.")); }
    finally { setSaving(false); }
  }

  async function remove(asset: MediaAsset) {
    if (!asset.can_delete || !window.confirm(`Xóa ${asset.display_name}?`)) return;
    setError(""); setMessage("");
    try {
      await deleteMediaAsset(asset.id);
      setAssets(current => current.filter(item => item.id !== asset.id));
      setMessage(`Đã xóa ${asset.display_name}.`);
    } catch (reason) { setError(errorText(reason, "Không thể xóa media.")); }
  }

  return <section className={`page media-library-page ${active ? "active" : ""}`}>
    <div className="media-library-heading"><strong>{assets.length}<small>media</small></strong><p>Quản lý nguồn video và hình ảnh được phép dùng trong mô phỏng.</p></div>
    <form className="media-upload-card" onSubmit={upload}>
      <label>Tên hiển thị<input aria-label="Tên hiển thị" value={displayName} onChange={event => setDisplayName(event.target.value)} required /></label>
      <label>Video hoặc hình ảnh<input aria-label="Video hoặc hình ảnh" name="media_file" type="file" accept="video/*,image/*" onChange={event => setFile(event.target.files?.[0])} required /></label>
      <button className="ppe-save-button" disabled={saving || !file || !displayName.trim()}>{saving ? "Đang tải lên…" : "Tải media lên"}</button>
    </form>
    {error && <p className="media-feedback error" role="alert">{error}</p>}
    {!error && message && <p className="media-feedback" role="status">{message}</p>}
    <div className="media-table-card">
      <table><thead><tr><th>Tên</th><th>Loại</th><th>Trạng thái</th><th>Thời điểm tải lên</th><th>Camera</th><th /></tr></thead>
        <tbody>{loading ? <tr><td colSpan={6}>Đang tải thư viện…</td></tr> : assets.length === 0 ? <tr><td colSpan={6}>Chưa có media nào.</td></tr> : assets.map(asset => <tr key={asset.id}>
          <td><strong>{asset.display_name}</strong>{asset.error_message && <small>{asset.error_message}</small>}</td>
          <td><span className="media-type-tag">{asset.media_type === "video" ? "Video" : "Hình ảnh"}</span></td>
          <td><span className={`asset-status ${asset.status.toLowerCase()}`}>{asset.status}</span></td>
          <td>{new Date(asset.uploaded_at).toLocaleString("vi-VN")}</td>
          <td>{asset.assigned_camera_id || "Chưa gán"}</td>
          <td><button className="danger-link" disabled={!asset.can_delete} title={asset.can_delete ? "Xóa media" : "Máy chủ không cho phép xóa media này"} onClick={() => void remove(asset)}>Xóa</button></td>
        </tr>)}</tbody>
      </table>
    </div>
  </section>;
});

function errorText(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
