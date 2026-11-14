"""Candidate Plan Builder (section 5): current practice, two alternatives, and the sample-only test plan."""
from dataclasses import dataclass

from app.domain.crops import TYPE_LABEL, CropProfile


@dataclass(frozen=True)
class CandidatePlan:
    code: str  # A-D
    crop: str
    role: str  # "current_practice", "alternative" or "sample_test"
    why_included: str


def build_plans(
    history: list[tuple[str, str]],
    current: str,
    supported: list[str],
    crops: dict[str, CropProfile],
    extra: list[str],
    candidate_season: str,
) -> list[CandidatePlan]:
    """history is [(season label, crop)], oldest first; current is the crop for Plan A, already checked."""
    last_season, last_crop = history[-1]
    if last_crop == current:
        why = f"Current practice: repeats the crop recorded for {last_season}."
    else:
        recorded = "unknown" if last_crop == "unknown" else f"{last_crop}, which this version cannot plan for"
        why = f"Current practice, as you chose it: the crop recorded for {last_season} is {recorded}."
    plans = [CandidatePlan("A", current, "current_practice", why)]
    # The MVP supports three candidate crops, so this always gives exactly two alternatives.
    for code, crop in zip("BC", [c for c in supported if c != current]):
        kind = TYPE_LABEL[crops[crop].crop_type]
        plans.append(CandidatePlan(
            code, crop, "alternative", f"Alternative: a supported {kind} for the {candidate_season} winter season."
        ))
    plans += [
        CandidatePlan("D", crop, "sample_test", "Sample test: shows how a crop this version does not support is rejected.")
        for crop in extra
    ]
    return plans
