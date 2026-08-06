import {useCallback, useEffect, useState} from "react";
import {loadPpeRequirements, savePpeRequirements} from "../../api/ppe-requirements";
import type {PpeRequirement, PpeRequirementUpdate} from "../../types";

interface PpeRequirementsPanelProps {
  cameraId: string;
  zoneId: string;
}

type LoadState = "loading" | "loaded" | "loadError";

const EMPTY_REQUIREMENT: PpeRequirementUpdate = {
  helmet_required: false,
  safety_glasses_required: false,
  gloves_required: false
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

  const update = useCallback((key: keyof PpeRequirementUpdate, value: boolean) => {
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
        <h2 id="ppe-requirements-title">Yêu cầu PPE</h2>
        <p>Chỉ cảnh báo loại đang bật khi model phát hiện thiếu.</p>
      </div>
      <div className="ppe-requirement-switches">
        <RequirementSwitch label="Yêu cầu mũ" checked={draft.helmet_required} disabled={saving}
          onChange={checked => update("helmet_required", checked)} />
        <RequirementSwitch label="Yêu cầu kính" checked={draft.safety_glasses_required} disabled={saving}
          onChange={checked => update("safety_glasses_required", checked)} />
        <RequirementSwitch label="Yêu cầu găng" checked={draft.gloves_required} disabled={saving}
          onChange={checked => update("gloves_required", checked)} />
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
    helmet_required: requirement.helmet_required,
    safety_glasses_required: requirement.safety_glasses_required,
    gloves_required: requirement.gloves_required
  };
}

function sameRequirement(left: PpeRequirementUpdate, right: PpeRequirementUpdate): boolean {
  return left.helmet_required === right.helmet_required
    && left.safety_glasses_required === right.safety_glasses_required
    && left.gloves_required === right.gloves_required;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
