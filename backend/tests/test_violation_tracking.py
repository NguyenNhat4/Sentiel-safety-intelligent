from uuid import UUID

from backend.app.services.violation_tracking_service import ViolationTrackingService


def test_continuous_violation_emits_one_occurrence():
    service = ViolationTrackingService()

    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)
    repeated = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.5)

    assert first[4][0].is_new is True
    assert repeated[4][0].is_new is False
    assert repeated[4][0].occurrence_id == first[4][0].occurrence_id
    UUID(first[4][0].occurrence_id)


def test_violation_rearms_only_after_confirmed_exit_and_cooldown():
    service = ViolationTrackingService(exit_confirm_frames=2, cooldown_seconds=2.0)
    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)[4][0]

    service.evaluate("session-a", {4: set()}, {4}, now=0.5)
    service.evaluate("session-a", {4: set()}, {4}, now=1.0)
    suppressed = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=2.0)[4][0]
    assert suppressed.occurrence_id == first.occurrence_id
    assert suppressed.is_new is False

    service.evaluate("session-a", {4: set()}, {4}, now=2.5)
    service.evaluate("session-a", {4: set()}, {4}, now=3.0)
    rearmed = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=5.1)[4][0]
    assert rearmed.occurrence_id != first.occurrence_id
    assert rearmed.is_new is True


def test_short_track_loss_does_not_create_a_new_occurrence():
    service = ViolationTrackingService(lost_grace_frames=3)
    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)[4][0]
    service.evaluate("session-a", {}, set(), now=0.5)
    service.evaluate("session-a", {}, set(), now=1.0)
    resumed = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=1.5)[4][0]

    assert resumed.occurrence_id == first.occurrence_id
    assert resumed.is_new is False


def test_tracks_and_rules_have_independent_occurrences():
    service = ViolationTrackingService()
    result = service.evaluate(
        "session-a",
        {4: {"zone_intrusion", "missing_ppe:helmet"}, 9: {"zone_intrusion"}},
        {4, 9},
        now=0.0,
    )

    assert len({item.occurrence_id for items in result.values() for item in items}) == 3
