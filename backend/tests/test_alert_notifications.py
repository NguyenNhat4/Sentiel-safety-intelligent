import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.integrations import telegram_notifications
from backend.app.integrations.telegram_notifications import TelegramNotificationAdapter
from backend.app.models.event import SafetyEvent
from backend.app.models.monitoring_zone import MonitoringZoneCollection, MonitoringZoneRecord
from backend.app.models.user import User, UserRole
from backend.app.services.alert_notification_service import AlertNotificationService
from backend.app.services.auth_service import hash_password


class RecordingTelegramAdapter:
    configured = True

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> None:
        self.messages.append((chat_id, text))


def test_telegram_adapter_posts_chat_id_and_text_to_bot_api(monkeypatch):
    requests = []

    class Response:
        def raise_for_status(self) -> None:
            return None

    class Client:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 4.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, str]):
            requests.append((url, json))
            return Response()

    monkeypatch.setattr(telegram_notifications.httpx, "AsyncClient", Client)

    asyncio.run(TelegramNotificationAdapter(" bot-token ", 4.0).send_message("-123456", "Confirmed"))

    assert requests == [
        (
            "https://api.telegram.org/botbot-token/sendMessage",
            {"chat_id": "-123456", "text": "Confirmed"},
        )
    ]


def test_confirmed_event_is_sent_only_to_its_assigned_area_manager():
    async def scenario():
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        db.add(
            User(
                email="area-two@sentinel.local",
                full_name="Area Two",
                role=UserRole.AREA_MANAGER.value,
                password_hash=hash_password("Temporary123!"),
                managed_area_id="zone_2",
                telegram_chat_id="area-two",
            )
        )
        db.add(
            User(
                email="area-three@sentinel.local",
                full_name="Area Three",
                role=UserRole.AREA_MANAGER.value,
                password_hash=hash_password("Temporary123!"),
                managed_area_id="zone_3",
                telegram_chat_id="area-three",
            )
        )
        db.commit()
        adapter = RecordingTelegramAdapter()

        queued = AlertNotificationService(adapter).queue_confirmed_events(
            db, [SafetyEvent(zone_id="zone_2", event_type="zone_intrusion", status="acknowledged")]
        )
        await asyncio.sleep(0)

        assert queued == 1
        assert [chat_id for chat_id, _ in adapter.messages] == ["area-two"]

    asyncio.run(scenario())


def test_confirmed_events_are_aggregated_with_specific_violation_labels():
    async def scenario():
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        db.add(MonitoringZoneCollection(camera_id="uploaded_video", revision=1))
        db.add(
            MonitoringZoneRecord(
                camera_id="uploaded_video",
                zone_id="zone_3",
                normalized_zone_id="zone_3",
                display_name="Khu vực 3",
                points=[],
                machine_state="running",
                enabled=True,
                order=0,
            )
        )
        db.add(
            User(
                email="area@sentinel.local",
                full_name="Area Manager",
                role=UserRole.AREA_MANAGER.value,
                password_hash=hash_password("Temporary123!"),
                managed_area_id="zone_3",
                telegram_username="@area_manager",
                telegram_chat_id="123456789",
            )
        )
        db.commit()
        adapter = RecordingTelegramAdapter()

        queued = AlertNotificationService(adapter).queue_confirmed_events(
            db,
            [
                SafetyEvent(
                    zone_id="zone_3",
                    event_type="missing_ppe",
                    status="acknowledged",
                    details={"violations": ["missing_ppe:hat", "missing_ppe:vest"]},
                ),
                SafetyEvent(
                    zone_id="zone_3",
                    event_type="zone_intrusion",
                    status="acknowledged",
                    details={"violations": ["zone_intrusion:zone_3"]},
                ),
            ],
        )
        await asyncio.sleep(0)

        assert queued == 1
        assert len(adapter.messages) == 1
        assert adapter.messages[0][0] == "123456789"
        assert "Khu vực 3" in adapter.messages[0][1]
        assert "có người vào vùng cấm" in adapter.messages[0][1]
        assert "mũ bảo hộ, áo phản quang" in adapter.messages[0][1]
        assert "Đã xác nhận" in adapter.messages[0][1]

    asyncio.run(scenario())


def test_unconfirmed_event_does_not_queue_telegram():
    async def scenario():
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        adapter = RecordingTelegramAdapter()

        queued = AlertNotificationService(adapter).queue_confirmed_events(
            db, [SafetyEvent(zone_id="zone_2", event_type="zone_intrusion", status="unacknowledged")]
        )
        await asyncio.sleep(0)

        assert queued == 0
        assert adapter.messages == []

    asyncio.run(scenario())
