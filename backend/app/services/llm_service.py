from typing import Optional, Dict, Any
from backend.app.core.config import get_settings


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

    def generate_recommendation(self, event_details: Dict[str, Any]) -> str:
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
            except Exception as e:
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
