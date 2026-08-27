import asyncio
import logging

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.integrations.telegram_notifications import TelegramNotificationAdapter
from backend.app.models.event import SafetyEvent
from backend.app.models.monitoring_zone import MonitoringZoneRecord
from backend.app.models.user import User, UserRole

logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()


class AlertNotificationService:
    """Routes human-confirmed safety violations to assigned area managers."""

    def __init__(self, adapter: TelegramNotificationAdapter | None = None) -> None:
        settings = get_settings()
        self._adapter = adapter or TelegramNotificationAdapter(
            settings.telegram_bot_token,
            settings.telegram_request_timeout_seconds,
        )

    def queue_confirmed_events(self, db: Session, events: list[SafetyEvent]) -> int:
        """Notify only the managers responsible for newly confirmed violations."""
        confirmed = [event for event in events if event.status == "acknowledged"]
        if not confirmed or not self._adapter.configured:
            return 0

        rules_by_area: dict[str, set[str]] = {}
        for event in confirmed:
            rules_by_area.setdefault(event.zone_id, set()).update(self._rules_for_event(event))
        area_names = dict(
            db.query(MonitoringZoneRecord.zone_id, MonitoringZoneRecord.display_name)
            .filter(MonitoringZoneRecord.zone_id.in_(rules_by_area))
            .all()
        )
        recipients = (
            db.query(User)
            .filter(
                User.role == UserRole.AREA_MANAGER.value,
                User.is_active.is_(True),
                User.managed_area_id.in_(rules_by_area),
                User.telegram_chat_id.is_not(None),
                User.telegram_chat_id != "",
            )
            .all()
        )
        for recipient in recipients:
            area_id = recipient.managed_area_id
            task = asyncio.create_task(
                self._deliver(
                    recipient.telegram_chat_id,
                    self._message(area_names.get(area_id, area_id), rules_by_area[area_id]),
                )
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        return len(recipients)

    async def _deliver(self, chat_id: str, text: str) -> None:
        try:
            await self._adapter.send_message(chat_id, text)
        except Exception:
            logger.exception("Telegram safety alert delivery failed")

    @staticmethod
    def _message(area_name: str, rules: set[str]) -> str:
        labels = []
        if any(rule.startswith("zone_intrusion") for rule in rules):
            labels.append("có người vào vùng cấm")
        if any(rule.startswith("restricted_area_person") for rule in rules):
            labels.append("phát hiện người trong khu vực hạn chế")
        missing = {rule.split(":", 1)[1] for rule in rules if rule.startswith("missing_ppe:")}
        if missing:
            ppe_labels = {"hat": "mũ bảo hộ", "vest": "áo phản quang"}
            labels.append("thiếu " + ", ".join(ppe_labels.get(item, item) for item in sorted(missing)))
        elif "missing_ppe" in rules:
            labels.append("thiếu PPE bắt buộc")
        if not labels:
            labels.append("vi phạm an toàn")
        return (
            f"SENTINEL - CẢNH BÁO AN TOÀN\nKhu vực: {area_name}\n"
            f"Đã xác nhận: {'; '.join(labels)}\nVui lòng mở hệ thống để xử lý."
        )

    @staticmethod
    def _rules_for_event(event: SafetyEvent) -> set[str]:
        details = event.details if isinstance(event.details, dict) else {}
        detail_rules = details.get("violations", [])
        if isinstance(detail_rules, list):
            rules = {str(rule) for rule in detail_rules if str(rule)}
            if rules:
                return rules

        context = event.decision_context if isinstance(event.decision_context, dict) else {}
        rule_context = context.get("rule", {}) if isinstance(context, dict) else {}
        context_rules = rule_context.get("triggered_rule_keys", []) if isinstance(rule_context, dict) else []
        if isinstance(context_rules, list):
            rules = {str(rule) for rule in context_rules if str(rule)}
            if rules:
                return rules

        if event.event_type == "missing_ppe_and_intrusion":
            return {"missing_ppe", "zone_intrusion"}
        return {event.event_type}


alert_notification_service = AlertNotificationService()
