import pytest

from backend.app.schemas.analysis import PersonPpeObservations, PpeObservation
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.safety_rule_engine import RulePersonObservation, SafetyRuleEngine


def person(*, inside_zone: bool = False, hat: str = "present", vest: str = "present") -> RulePersonObservation:
    return RulePersonObservation(
        confidence=0.9,
        inside_zone=inside_zone,
        ppe=PersonPpeObservations(
            hat=PpeObservation(status=hat, confidence=None if hat == "missing" else 0.9),
            vest=PpeObservation(status=vest, confidence=None if vest == "missing" else 0.9),
        ),
    )


def requirements(*, hat_required: bool = False, vest_required: bool = False) -> PpeRequirementResponse:
    return PpeRequirementResponse(
        camera_id="uploaded_video",
        zone_id="zone_01",
        profile="hat_vest_v1",
        hat_required=hat_required,
        vest_required=vest_required,
        updated_at=None,
    )


def test_returns_normal_when_observations_match_configured_rules():
    result = SafetyRuleEngine().evaluate(
        people=[person()], requirements=requirements(hat_required=True), machine_state="running", zone_active=False
    )

    assert result.outcome == "normal"
    assert result.review_required is False


def test_returns_violate_and_review_for_required_missing_ppe():
    result = SafetyRuleEngine().evaluate(
        people=[person(hat="missing")],
        requirements=requirements(hat_required=True),
        machine_state="running",
        zone_active=False,
    )

    assert result.outcome == "violate"
    assert result.review_required is True
    assert result.missing_required_ppe == [["hat"]]


def test_required_ppe_alerts_are_independent_of_machine_state():
    result = SafetyRuleEngine().evaluate(
        people=[person(hat="missing")],
        requirements=requirements(hat_required=True),
        machine_state="stopped",
        zone_active=False,
    )

    assert result.outcome == "violate"
    assert result.review_required is True
    assert result.ppe_alert is True
    assert result.missing_required_ppe == [["hat"]]


def test_evaluates_hat_and_vest_independently_for_multiple_people():
    result = SafetyRuleEngine().evaluate(
        people=[person(hat="missing"), person(vest="missing")],
        requirements=requirements(hat_required=True, vest_required=True),
        machine_state="running",
        zone_active=False,
    )

    assert result.missing_required_ppe == [["hat"], ["vest"]]
    assert result.ppe_alert is True


@pytest.mark.parametrize(("machine_state", "expected"), [("running", "violate"), ("stopped", "normal")])
def test_active_zone_requires_a_running_machine(machine_state, expected):
    result = SafetyRuleEngine().evaluate(
        people=[person(inside_zone=True)], requirements=requirements(), machine_state=machine_state, zone_active=True
    )

    assert result.outcome == expected
    assert result.person_inside_zone is True


@pytest.mark.parametrize(
    ("hat_required", "vest_required", "people", "machine_state", "zone_active", "expected_outcome"),
    [
        # Required PPE is present: machine state alone does not create a violation.
        (True, True, [person()], "running", False, "normal"),
        (True, True, [person()], "stopped", False, "normal"),
        # Each required PPE item is evaluated independently.
        (True, False, [person(hat="missing")], "running", False, "violate"),
        (False, True, [person(vest="missing")], "running", False, "violate"),
        (True, True, [person(hat="missing", vest="missing")], "running", False, "violate"),
        # No detected person means there is no PPE or zone violation.
        (True, True, [], "running", False, "normal"),
        # Any person can trigger the aggregate result.
        (True, True, [person(), person(hat="missing")], "running", False, "violate"),
        # Zone entry is a violation only while its machine is running.
        (False, False, [person(inside_zone=True)], "running", True, "violate"),
        (False, False, [person(inside_zone=True)], "stopped", True, "normal"),
    ],
)
def test_evaluates_hat_vest_zone_and_person_count_truth_table(
    hat_required,
    vest_required,
    people,
    machine_state,
    zone_active,
    expected_outcome,
):
    result = SafetyRuleEngine().evaluate(
        people=people,
        requirements=requirements(hat_required=hat_required, vest_required=vest_required),
        machine_state=machine_state,
        zone_active=zone_active,
    )

    assert result.outcome == expected_outcome
    assert result.review_required is (expected_outcome == "violate")
