import asyncio
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models.event import SafetyEvent
from backend.app.models.monitoring_zone import MonitoringZoneCollection, MonitoringZoneRecord
from backend.app.models.user import User, UserRole
from backend.app.schemas.analysis import FrameInferenceResponse
from backend.app.services.alert_notification_service import AlertNotificationService
from backend.app.services.auth_service import hash_password


class RecordingTelegramAdapter:
    configured = True

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> None:
        self.messages.append((chat_id, text))


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


def test_new_alert_is_sent_once_to_manager_assigned_to_the_area():
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
        result = FrameInferenceResponse.model_validate(
            {
                "result": "violate",
                "review_required": True,
                "has_active_violation": True,
                "detections": [],
                "snapshot_data": None,
                "rule": {},
                "people": [
                    {
                        "track_id": 2,
                        "bbox": [0, 0, 10, 20],
                        "confidence": 0.9,
                        "foot_point": [5, 20],
                        "inside_zone": False,
                        "zone_memberships": [],
                        "ppe": {
                            "hat": {"status": "missing", "confidence": None},
                            "vest": {"status": "missing", "confidence": None},
                        },
                        "missing_required_ppe": ["hat", "vest"],
                        "active_violations": [
                            {
                                "occurrence_id": str(uuid4()),
                                "rule_key": "missing_ppe:hat",
                                "zone_id": None,
                                "is_new": True,
                            },
                            {
                                "occurrence_id": str(uuid4()),
                                "rule_key": "missing_ppe:vest",
                                "zone_id": None,
                                "is_new": True,
                            },
                        ],
                    }
                ],
            }
        )
        adapter = RecordingTelegramAdapter()

        queued = AlertNotificationService(adapter).queue_new_alerts(db, result, fallback_area_id="zone_3")
        await asyncio.sleep(0)

        assert queued == 1
        assert len(adapter.messages) == 1
        assert adapter.messages[0][0] == "123456789"
        assert "Khu vực 3" in adapter.messages[0][1]
        assert "mũ bảo hộ, áo phản quang" in adapter.messages[0][1]

    asyncio.run(scenario())
