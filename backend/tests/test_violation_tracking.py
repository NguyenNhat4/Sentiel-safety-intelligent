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


def test_one_person_emits_only_one_alert_for_entire_video_session():
    service = ViolationTrackingService(exit_confirm_frames=1, cooldown_seconds=0.0, ppe_confirmation_frames=1)

    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)[4]
    service.evaluate("session-a", {4: set()}, {4}, now=1.0)
    second_rule = service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=2.0)[4]

    assert first[0].is_new is True
    assert second_rule[0].is_new is False


def test_same_person_reviolation_after_clear_does_not_request_review_again():
    service = ViolationTrackingService(exit_confirm_frames=1, cooldown_seconds=0.0)

    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)[4][0]
    service.evaluate("session-a", {4: set()}, {4}, now=1.0)
    repeated = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=2.0)[4][0]

    assert repeated.occurrence_id == first.occurrence_id
    assert repeated.is_new is False


def test_violation_requires_four_consecutive_frames_before_opening_an_alert():
    service = ViolationTrackingService(activation_frames=4)

    for frame in range(1, 4):
        pending = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=float(frame))
        assert pending[4] == []

    opened = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=4.0)

    assert opened[4][0].is_new is True


def test_interrupted_pending_violation_must_restart_its_consecutive_frame_count():
    service = ViolationTrackingService(activation_frames=4)
    for frame in range(1, 4):
        service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=float(frame))
    service.evaluate("session-a", {4: set()}, {4}, now=4.0)

    for frame in range(5, 8):
        pending = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=float(frame))
        assert pending[4] == []


def test_violation_rearms_without_a_second_alert_in_the_same_session():
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
    assert rearmed.occurrence_id == first.occurrence_id
    assert rearmed.is_new is False


def test_short_track_loss_does_not_create_a_new_occurrence():
    service = ViolationTrackingService(lost_grace_frames=3)
    first = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=0.0)[4][0]
    service.evaluate("session-a", {}, set(), now=0.5)
    service.evaluate("session-a", {}, set(), now=1.0)
    resumed = service.evaluate("session-a", {4: {"zone_intrusion"}}, {4}, now=1.5)[4][0]

    assert resumed.occurrence_id == first.occurrence_id
    assert resumed.is_new is False


def test_nearby_track_id_handoff_keeps_occurrence_while_person_exits():
    service = ViolationTrackingService(track_handoff_max_distance=0.12)
    first = service.evaluate(
        "session-a",
        {4: {"zone_intrusion"}},
        {4},
        track_positions={4: (0.48, 0.72)},
        now=0.0,
    )[4][0]

    handed_off = service.evaluate(
        "session-a",
        {9: {"zone_intrusion"}},
        {9},
        track_positions={9: (0.51, 0.73)},
        now=0.5,
    )[9][0]

    assert handed_off.occurrence_id == first.occurrence_id
    assert handed_off.is_new is False


def test_distant_new_track_still_opens_an_independent_occurrence():
    service = ViolationTrackingService(track_handoff_max_distance=0.12)
    first = service.evaluate(
        "session-a",
        {4: {"zone_intrusion"}},
        {4},
        track_positions={4: (0.20, 0.70)},
        now=0.0,
    )[4][0]

    distant = service.evaluate(
        "session-a",
        {9: {"zone_intrusion"}},
        {9},
        track_positions={9: (0.80, 0.70)},
        now=0.5,
    )[9][0]

    assert distant.occurrence_id != first.occurrence_id
    assert distant.is_new is True


def test_track_handoff_after_lost_grace_opens_a_new_occurrence():
    service = ViolationTrackingService(lost_grace_frames=2, track_handoff_max_distance=0.12)
    first = service.evaluate(
        "session-a",
        {4: {"zone_intrusion"}},
        {4},
        track_positions={4: (0.48, 0.72)},
        now=0.0,
    )[4][0]
    service.evaluate("session-a", {}, set(), now=0.5)
    service.evaluate("session-a", {}, set(), now=1.0)

    replacement = service.evaluate(
        "session-a",
        {9: {"zone_intrusion"}},
        {9},
        track_positions={9: (0.50, 0.73)},
        now=1.5,
    )[9][0]

    assert replacement.occurrence_id != first.occurrence_id
    assert replacement.is_new is True


def test_tracks_and_rules_have_independent_occurrences():
    service = ViolationTrackingService(ppe_confirmation_frames=1)
    result = service.evaluate(
        "session-a",
        {4: {"zone_intrusion", "missing_ppe:hat"}, 9: {"zone_intrusion"}},
        {4, 9},
        now=0.0,
    )

    assert len({item.occurrence_id for items in result.values() for item in items}) == 3


def test_ppe_candidate_requires_six_consecutive_missing_frames_before_opening_occurrence():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(5):
        assert service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=float(frame))[4] == []
    opened = service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=5.0)[4]

    assert len(opened) == 1
    assert opened[0].rule_key == "missing_ppe:hat"
    assert opened[0].is_new is True


def test_unreviewed_ppe_log_requires_two_continuous_present_seconds_to_retract():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(5):
        service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=float(frame))
    opened = service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=5.0)[4][0]
    for now in (6.0, 6.4, 6.8, 7.2, 7.99):
        still_active = service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=now)[4]
        assert still_active[0].occurrence_id == opened.occurrence_id
    retracted = service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=8.0)[4]

    assert opened.is_new is True
    assert retracted == []


def test_missing_ppe_stays_active_without_an_explicit_present_observation():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(5):
        service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=float(frame))
    opened = service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=5.0)[4][0]
    later_result = service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=6.0)[4][0]

    assert later_result.occurrence_id == opened.occurrence_id
    assert later_result.is_new is False


def test_each_present_ppe_item_retracts_only_its_own_warning_after_two_seconds():
    service = ViolationTrackingService(ppe_confirmation_frames=6)
    both_missing = {4: {"missing_ppe:hat", "missing_ppe:vest"}}

    for frame in range(5):
        service.evaluate("session-a", both_missing, {4}, now=float(frame))
    opened = service.evaluate("session-a", both_missing, {4}, now=5.0)[4]
    for now in (6.0, 6.5, 7.0, 7.99):
        pending = service.evaluate(
            "session-a",
            {4: {"missing_ppe:vest"}},
            {4},
            ppe_present_items={4: {"hat"}},
            now=now,
        )[4]
        assert {item.rule_key for item in pending} == {"missing_ppe:hat", "missing_ppe:vest"}
    updated = service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, ppe_present_items={4: {"hat"}}, now=8.0)[4]

    assert {item.rule_key for item in opened} == {"missing_ppe:hat", "missing_ppe:vest"}
    assert [item.rule_key for item in updated] == ["missing_ppe:vest"]


def test_unknown_ppe_does_not_retract_an_active_warning():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(5):
        service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=float(frame))
    opened = service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=5.0)[4][0]
    unknown_result = service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: set()}, now=5.1)[4][0]

    assert unknown_result.occurrence_id == opened.occurrence_id


def test_ppe_warning_retracts_when_requirement_is_no_longer_applicable():
    service = ViolationTrackingService(ppe_confirmation_frames=1)
    rule = "missing_ppe:hat"
    opened = service.evaluate(
        "session-a",
        {4: {rule}},
        {4},
        applicable_ppe_rules={(4, rule)},
        now=0.0,
    )[4][0]

    retracted = service.evaluate(
        "session-a",
        {4: set()},
        {4},
        applicable_ppe_rules=set(),
        now=0.5,
    )[4]

    assert opened.is_new is True
    assert retracted == []


def test_unknown_or_missing_resets_the_two_second_present_retraction_window():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(6):
        opened = service.evaluate("session-a", {4: {"missing_ppe:hat"}}, {4}, now=float(frame))[4]
    occurrence_id = opened[0].occurrence_id
    service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=6.0)
    service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=7.99)
    service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: set()}, now=8.0)
    for now in (8.1, 9.0, 10.09):
        still_active = service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=now)[4]
        assert still_active[0].occurrence_id == occurrence_id
    assert service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"hat"}}, now=10.1)[4] == []


def test_two_second_ppe_retraction_is_isolated_by_track_id():
    service = ViolationTrackingService(ppe_confirmation_frames=6)
    missing = {4: {"missing_ppe:hat"}, 9: {"missing_ppe:hat"}}

    for frame in range(5):
        service.evaluate("session-a", missing, {4, 9}, now=float(frame))
    opened = service.evaluate("session-a", missing, {4, 9}, now=5.0)
    for now in (6.0, 7.0, 8.0):
        updated = service.evaluate(
            "session-a",
            {4: set(), 9: {"missing_ppe:hat"}},
            {4, 9},
            ppe_present_items={4: {"hat"}},
            now=now,
        )

    assert updated[4] == []
    assert updated[9][0].occurrence_id == opened[9][0].occurrence_id


def test_zone_debounce_does_not_delay_a_restricted_area_alert():
    service = ViolationTrackingService(zone_activation_frames=4)

    for frame in range(1, 4):
        result = service.evaluate("session-a", {4: {"zone_intrusion", "restricted_area_person"}}, {4}, now=float(frame))
        assert [item.rule_key for item in result[4]] == ["restricted_area_person"]

    opened = service.evaluate("session-a", {4: {"zone_intrusion", "restricted_area_person"}}, {4}, now=4.0)[4]
    assert {item.rule_key for item in opened} == {"zone_intrusion", "restricted_area_person"}


def test_ppe_candidate_restarts_after_the_missing_sequence_is_interrupted():
    service = ViolationTrackingService(ppe_confirmation_frames=6)

    for frame in range(5):
        service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=float(frame))
    service.evaluate("session-a", {4: set()}, {4}, ppe_present_items={4: {"vest"}}, now=5.0)
    assert service._confirmed_ppe_items[("session-a", 4)] == {"vest"}
    for frame in range(6, 11):
        assert service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=float(frame))[4] == []
    assert service._confirmed_ppe_items[("session-a", 4)] == {"vest"}
    opened = service.evaluate("session-a", {4: {"missing_ppe:vest"}}, {4}, now=11.0)[4]

    assert opened[0].is_new is True
    assert service._confirmed_ppe_items[("session-a", 4)] == set()
