import asyncio
import logging

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.integrations.telegram_notifications import TelegramNotificationAdapter
from backend.app.models.event import SafetyEvent
from backend.app.models.monitoring_zone import MonitoringZoneRecord
from backend.app.models.user import User, UserRole
from backend.app.schemas.analysis import FrameInferenceResponse

logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()


class AlertNotificationService:
    """Routes newly opened safety occurrences to assigned area managers."""

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

        event_by_area = {event.zone_id: event for event in confirmed}
        area_names = dict(
            db.query(MonitoringZoneRecord.zone_id, MonitoringZoneRecord.display_name)
            .filter(MonitoringZoneRecord.zone_id.in_(event_by_area))
            .all()
        )
        recipients = (
            db.query(User)
            .filter(
                User.role == UserRole.AREA_MANAGER.value,
                User.is_active.is_(True),
                User.managed_area_id.in_(event_by_area),
                User.telegram_chat_id.is_not(None),
            )
            .all()
        )
        for recipient in recipients:
            event = event_by_area[recipient.managed_area_id]
            task = asyncio.create_task(
                self._deliver(
                    recipient.telegram_chat_id,
                    self._message(area_names.get(event.zone_id, event.zone_id), {event.event_type}),
                )
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        return len(recipients)

    def queue_new_alerts(
        self,
        db: Session,
        result: FrameInferenceResponse,
        *,
        fallback_area_id: str,
    ) -> int:
        new_rules_by_area: dict[str, set[str]] = {}
        for person in result.people:
            for violation in person.active_violations:
                if not violation.is_new:
                    continue
                area_id = violation.zone_id or fallback_area_id
                new_rules_by_area.setdefault(area_id, set()).add(violation.rule_key)
        if not new_rules_by_area or not self._adapter.configured:
            return 0

        area_names = dict(
            db.query(MonitoringZoneRecord.zone_id, MonitoringZoneRecord.display_name)
            .filter(MonitoringZoneRecord.zone_id.in_(new_rules_by_area))
            .all()
        )
        recipients = (
            db.query(User)
            .filter(
                User.role == UserRole.AREA_MANAGER.value,
                User.is_active.is_(True),
                User.managed_area_id.in_(new_rules_by_area),
                User.telegram_chat_id.is_not(None),
            )
            .all()
        )
        for recipient in recipients:
            area_id = recipient.managed_area_id
            task = asyncio.create_task(
                self._deliver(
                    recipient.telegram_chat_id,
                    self._message(area_names.get(area_id, area_id), new_rules_by_area.get(area_id, set())),
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
        if "person_safety_violation" in rules:
            labels.append("person safety violation")
        missing = {rule.split(":", 1)[1] for rule in rules if rule.startswith("missing_ppe:")}
        if missing:
            ppe_labels = {"hat": "mũ bảo hộ", "vest": "áo phản quang"}
            labels.append("thiếu " + ", ".join(ppe_labels.get(item, item) for item in sorted(missing)))
        return f"SENTINEL - CẢNH BÁO AN TOÀN\nKhu vực: {area_name}\nPhát hiện: {'; '.join(labels)}\nVui lòng mở hệ thống để review."


alert_notification_service = AlertNotificationService()
