import {useCallback, useEffect, useState} from "react";
import {cameraStreamUrl, getStreamConfiguration} from "../../api/stream-config";
import "./stream.css";

export function StreamViewer() {
  const [cameraId, setCameraId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setCameraId((await getStreamConfiguration()).active_camera_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể tải cấu hình stream."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="stream-empty-state"><strong>Đang tải stream</strong><span>Đang kiểm tra camera active.</span></div>;
  if (error) return <div className="stream-empty-state"><strong>Không thể tải stream</strong><span>{error}</span><button className="secondary-btn" onClick={() => void load()}>Thử lại</button></div>;
  if (!cameraId) return <div className="stream-empty-state"><strong>Chưa có stream được bật</strong><span>System Admin cần bật một camera trong Quản trị hệ thống.</span></div>;
  return <div className="active-stream-view"><img src={cameraStreamUrl(cameraId)} alt={`Live stream ${cameraId}`} /><div className="stream-badge"><i className="live-dot" /> LIVE · {cameraId}</div><small>MJPEG preview · AI inference chưa được nối trong phase này</small></div>;
}
