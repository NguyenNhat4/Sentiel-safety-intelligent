import json
from typing import Any

from backend.app.core.config import get_settings
from backend.app.schemas.event import EventIncidentSummary


def get_llm():
    """Instantiate ChatOpenAI using settings if API key is provided."""
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "sk-your-key-here":
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
        )
    except Exception:
        return None


class SafetyAgentService:
    def __init__(self):
        self.llm = get_llm()

    def generate_recommendation(self, event_details: dict[str, Any]) -> str:
        """Generate safety recommendations for an incident or violation."""
        event_type = event_details.get("event_type", "unknown")
        zone_id = event_details.get("zone_id", "unknown")
        severity = event_details.get("severity", "medium")

        if self.llm:
            try:
                prompt = (
                    f"As a Safety Officer AI Agent, provide actionable safety recommendations "
                    f"for a {severity} severity '{event_type}' violation in {zone_id}."
                )
                response = self.llm.invoke(prompt)
                return str(response.content)
            except Exception:
                pass

        # Rule-based fallback recommendation if LLM is unavailable/offline
        if "intrusion" in event_type:
            return (
                f"[{severity.upper()}] Intrusion detected in {zone_id}. "
                "Immediately halt machinery operations in the zone and notify the zone supervisor."
            )
        elif "missing_ppe" in event_type:
            return (
                f"[{severity.upper()}] Missing PPE detected in {zone_id}. "
                "Issue a warning to the personnel and provide required helmet/safety gear before resuming task."
            )
        return f"[{severity.upper()}] Safety event logged in {zone_id}. Perform routine safety inspection."

    def generate_incident_summary(
        self,
        *,
        decision_context: dict[str, Any] | None,
        event_type: str,
        zone_id: str,
    ) -> EventIncidentSummary:
        deterministic = self._deterministic_incident_summary(
            decision_context=decision_context,
            event_type=event_type,
            zone_id=zone_id,
        )
        if not decision_context or not self.llm:
            return EventIncidentSummary(
                text=deterministic,
                source="deterministic",
                context_schema_version=(decision_context or {}).get("schema_version"),
            )
        try:
            facts = self._incident_summary_facts(decision_context)
            prompt = (
                "Tóm tắt sự việc an toàn sau bằng tối đa hai câu tiếng Việt. "
                "Chỉ dùng dữ kiện có trong JSON, không suy đoán, không thêm khuyến nghị. "
                f"Incident facts: {json.dumps(facts, ensure_ascii=False)}"
            )
            response = self.llm.invoke(prompt)
            text = str(response.content).strip()
            if text:
                return EventIncidentSummary(
                    text=text[:1200],
                    source="llm",
                    context_schema_version=decision_context.get("schema_version"),
                )
        except Exception:
            pass
        return EventIncidentSummary(
            text=deterministic,
            source="deterministic",
            context_schema_version=decision_context.get("schema_version"),
        )

    @staticmethod
    def _incident_summary_facts(decision_context: dict[str, Any]) -> dict[str, Any]:
        scene = decision_context["scene"]
        decision = decision_context["system_decision"]
        review = decision_context["human_review"]
        return {
            "schema_version": decision_context.get("schema_version"),
            "zone_name": scene.get("zone_name"),
            "machine_state": scene.get("machine_state"),
            "people_count": len(scene.get("people") or []),
            "result": decision.get("result"),
            "reasons": [SafetyAgentService._reason_label(reason) for reason in decision.get("reason_codes") or []],
            "severity": decision.get("severity"),
            "review_outcome": review.get("outcome"),
        }

    @staticmethod
    def _deterministic_incident_summary(
        *,
        decision_context: dict[str, Any] | None,
        event_type: str,
        zone_id: str,
    ) -> str:
        if not decision_context:
            return (
                f"Sự kiện {event_type} tại {zone_id} không có decision context đầy đủ "
                "do được tạo bởi phiên bản hệ thống cũ."
            )
        scene = decision_context["scene"]
        decision = decision_context["system_decision"]
        review = decision_context["human_review"]
        zone_name = scene.get("zone_name") or scene.get("zone_id") or zone_id
        machine_state = "đang chạy" if scene.get("machine_state") == "running" else "đã dừng"
        people_count = len(scene.get("people") or [])
        outcome = "vi phạm thực tế" if review.get("outcome") == "actual_violation" else "báo sai"
        reason_labels = []
        for reason in decision.get("reason_codes") or []:
            reason_labels.append(SafetyAgentService._reason_label(reason))
        reasons = " và ".join(reason_labels) or "không rõ nguyên nhân"
        return (
            f"Tại {zone_name}, hệ thống phát hiện {people_count} người khi máy {machine_state} "
            f"và đánh dấu là vi phạm do {reasons}. "
            f"{review.get('actor_name', 'Cán bộ an toàn')} xác nhận đây là {outcome}."
        )

    @staticmethod
    def _reason_label(reason: str) -> str:
        if reason.startswith("zone_intrusion"):
            return "xâm nhập vùng cấm"
        if reason.startswith(("missing_required_ppe:", "missing_ppe:")):
            item = reason.rsplit(":", 1)[-1]
            return {"hat": "thiếu mũ bảo hộ", "vest": "thiếu áo phản quang"}.get(item, "thiếu PPE")
        return reason
