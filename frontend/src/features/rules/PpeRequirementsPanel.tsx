import {useCallback, useEffect, useState} from "react";
import {loadPpeRequirements, savePpeRequirements} from "../../api/ppe-requirements";
import type {PpeRequirement, PpeRequirementUpdate} from "../../types";

interface PpeRequirementsPanelProps {
  cameraId: string;
  zoneId: string;
}

type LoadState = "loading" | "loaded" | "loadError";

const EMPTY_REQUIREMENT: PpeRequirementUpdate = {
  profile: "hat_vest_v1",
  hat_required: false,
  vest_required: false,
  restricted_area_detection_enabled: false
};

export function PpeRequirementsPanel({cameraId, zoneId}: PpeRequirementsPanelProps) {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [saved, setSaved] = useState<PpeRequirementUpdate>(EMPTY_REQUIREMENT);
  const [draft, setDraft] = useState<PpeRequirementUpdate>(EMPTY_REQUIREMENT);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadState("loading");
    setError(undefined);
    setMessage(undefined);
    void loadPpeRequirements(cameraId, zoneId)
      .then(requirement => {
        if (!active) return;
        const values = toUpdate(requirement);
        setSaved(values);
        setDraft(values);
        setLoadState("loaded");
      })
      .catch(loadError => {
        if (!active) return;
        setError(errorMessage(loadError, "Không thể tải cấu hình PPE"));
        setLoadState("loadError");
      });
    return () => { active = false; };
  }, [cameraId, reloadKey, zoneId]);

  const update = useCallback((key: "hat_required" | "vest_required" | "restricted_area_detection_enabled", value: boolean) => {
    setDraft(current => ({...current, [key]: value}));
    setError(undefined);
    setMessage(undefined);
  }, []);

  const dirty = !sameRequirement(saved, draft);

  async function save(): Promise<void> {
    setSaving(true);
    setError(undefined);
    setMessage(undefined);
    try {
      const response = await savePpeRequirements(cameraId, zoneId, draft);
      const persisted = toUpdate(response);
      setSaved(persisted);
      setDraft(persisted);
      setMessage("Đã lưu cấu hình");
    } catch (saveError) {
      setError(errorMessage(saveError, "Không thể lưu cấu hình PPE"));
    } finally {
      setSaving(false);
    }
  }

  if (loadState === "loading") {
    return <section className="ppe-requirements loading" role="status" aria-live="polite">Đang tải cấu hình PPE…</section>;
  }

  if (loadState === "loadError") {
    return (
      <section className="ppe-requirements error-state">
        <p role="alert">{error}</p>
        <button type="button" className="secondary-btn" onClick={() => setReloadKey(key => key + 1)}>Thử tải lại</button>
      </section>
    );
  }

  return (
    <section className="ppe-requirements" aria-labelledby="ppe-requirements-title">
      <div className="ppe-requirements-copy">
        <small>CAMERA · KHU VỰC</small>
        <h2 id="ppe-requirements-title">Cấu hình cảnh báo</h2>
        <p>Thiết lập riêng cho khu vực đang chọn.</p>
      </div>
      <div className="ppe-requirement-switches">
        <RequirementSwitch label="Yêu cầu mũ bảo hộ" checked={draft.hat_required} disabled={saving}
          onChange={checked => update("hat_required", checked)} />
        <RequirementSwitch label="Yêu cầu áo phản quang" checked={draft.vest_required} disabled={saving}
          onChange={checked => update("vest_required", checked)} />
        <RequirementSwitch label="Detect vùng cấm" checked={Boolean(draft.restricted_area_detection_enabled)} disabled={saving}
          onChange={checked => update("restricted_area_detection_enabled", checked)} />
      </div>
      <div className="ppe-requirement-actions">
        <div className="ppe-save-status" aria-live="polite">
          {error && <span role="alert">{error}</span>}
          {!error && message && <span>{message}</span>}
          {!error && !message && dirty && <span>Chưa lưu thay đổi</span>}
        </div>
        <button type="button" className="ppe-save-button" disabled={!dirty || saving} onClick={() => void save()}>
          {saving ? "Đang lưu…" : error ? "Thử lưu lại" : "Lưu cấu hình"}
        </button>
      </div>
    </section>
  );
}

interface RequirementSwitchProps {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}

function RequirementSwitch({label, checked, disabled, onChange}: RequirementSwitchProps) {
  return (
    <label className="ppe-switch-row">
      <span>{label}</span>
      <input type="checkbox" aria-label={label} checked={checked} disabled={disabled}
        onChange={event => onChange(event.target.checked)} />
      <i aria-hidden="true"><b /></i>
      <em>{checked ? "ON" : "OFF"}</em>
    </label>
  );
}

function toUpdate(requirement: PpeRequirement): PpeRequirementUpdate {
  return {
    profile: requirement.profile,
    hat_required: requirement.hat_required,
    vest_required: requirement.vest_required,
    restricted_area_detection_enabled: requirement.restricted_area_detection_enabled ?? false
  };
}

function sameRequirement(left: PpeRequirementUpdate, right: PpeRequirementUpdate): boolean {
  return left.profile === right.profile
    && left.hat_required === right.hat_required
    && left.vest_required === right.vest_required
    && left.restricted_area_detection_enabled === right.restricted_area_detection_enabled;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
