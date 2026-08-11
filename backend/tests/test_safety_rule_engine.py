from backend.app.schemas.analysis import PersonPpeObservations, PpeObservation
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.safety_rule_engine import RulePersonObservation, SafetyRuleEngine


def person(*, inside_zone: bool = False, helmet: str = "present") -> RulePersonObservation:
    return RulePersonObservation(
        confidence=0.9,
        inside_zone=inside_zone,
        ppe=PersonPpeObservations(
            helmet=PpeObservation(status=helmet, confidence=None if helmet == "missing" else 0.9),
            safety_glasses=PpeObservation(status="unknown", confidence=None),
            gloves=PpeObservation(status="unknown", confidence=None),
        ),
    )


def requirements(*, helmet_required: bool = False) -> PpeRequirementResponse:
    return PpeRequirementResponse(
        camera_id="uploaded_video",
        zone_id="zone_01",
        helmet_required=helmet_required,
        safety_glasses_required=False,
        gloves_required=False,
        updated_at=None,
    )


def test_returns_normal_when_observations_match_configured_rules():
    result = SafetyRuleEngine().evaluate(
        people=[person()], requirements=requirements(helmet_required=True), machine_state="running", zone_active=False
    )

    assert result.outcome == "normal"
    assert result.review_required is False


def test_returns_violate_and_review_for_required_missing_ppe():
    result = SafetyRuleEngine().evaluate(
        people=[person(helmet="missing")],
        requirements=requirements(helmet_required=True),
        machine_state="stopped",
        zone_active=False,
    )

    assert result.outcome == "violate"
    assert result.review_required is True
    assert result.missing_required_ppe == [["helmet"]]


def test_returns_violate_for_person_in_active_zone_while_machine_runs():
    result = SafetyRuleEngine().evaluate(
        people=[person(inside_zone=True)], requirements=requirements(), machine_state="running", zone_active=True
    )

    assert result.outcome == "violate"
    assert result.person_inside_zone is True
