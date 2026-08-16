from dataclasses import dataclass
from typing import Literal

from backend.app.schemas.analysis import PersonPpeObservations
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.ppe_requirement_service import PpeStatus, should_alert_for_missing_ppe


@dataclass(frozen=True)
class RulePersonObservation:
    confidence: float
    inside_zone: bool
    ppe: PersonPpeObservations


@dataclass(frozen=True)
class RuleEvaluationResult:
    outcome: Literal["normal", "violate"]
    review_required: bool
    person_inside_zone: bool
    ppe_alert: bool
    missing_required_ppe: list[list[str]]


class SafetyRuleEngine:
    def __init__(self, person_confidence_threshold: float = 0.5) -> None:
        self._person_confidence_threshold = person_confidence_threshold

    def evaluate(
        self,
        *,
        people: list[RulePersonObservation],
        requirements: PpeRequirementResponse,
        machine_state: Literal["running", "stopped"],
        zone_active: bool,
    ) -> RuleEvaluationResult:
        missing = [self._missing_for_person(person, requirements) for person in people]
        ppe_alert = any(missing)
        person_inside_zone = zone_active and any(person.inside_zone for person in people)
        violation = ppe_alert or person_inside_zone
        return RuleEvaluationResult(
            outcome="violate" if violation else "normal",
            review_required=violation,
            person_inside_zone=person_inside_zone,
            ppe_alert=ppe_alert,
            missing_required_ppe=missing,
        )

    def _missing_for_person(self, person: RulePersonObservation, requirements: PpeRequirementResponse) -> list[str]:
        items = (
            ("hat", requirements.hat_required, person.ppe.hat),
            ("vest", requirements.vest_required, person.ppe.vest),
        )
        return [
            name
            for name, required, observation in items
            if should_alert_for_missing_ppe(
                required=required,
                status=PpeStatus(observation.status),
                person_confidence=person.confidence,
                threshold=self._person_confidence_threshold,
                association_is_valid=True,
            )
        ]
