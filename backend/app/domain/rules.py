"""Hard constraints H1-H3 and criterion rules R1-R6 (section 18)."""
from dataclasses import dataclass

from app.domain.crops import CropProfile
from app.services.indicators import Indicators, seasons_meeting
from app.services.site_check import SiteCheck

RULES_VERSION = "0.1"  # matches rotation_rule.version in db/seed.sql
IRRIGATED_ONLY: set[str] = set()  # no MVP crop is irrigated-only, so H3 cannot trip yet


@dataclass(frozen=True)
class CriterionResult:
    criterion: str  # "hard_constraint", "rotation_soil", "water_fit" or "risk"
    label: str  # "rejected", "favorable", "mixed", "concern" or "insufficient_evidence"
    rule: str | None  # None only for a rotation result that no single rule produced
    reason: str


def hard_constraint(crop: str, crops: dict[str, CropProfile], irrigation: str) -> CriterionResult | None:
    """H1-H3, checked before anything else. None means the plan may be evaluated."""
    profile = crops.get(crop)
    if profile is None or profile.season is None:
        return CriterionResult("hard_constraint", "rejected", "H1", "This crop is not supported in this version.")
    if profile.season != "winter":  # the MVP candidate season, 2026/27, is a winter season
        return CriterionResult(
            "hard_constraint", "rejected", "H2", "This crop is not grown in the selected season in this version."
        )
    if crop in IRRIGATED_ONLY and irrigation == "rain-fed":
        return CriterionResult(
            "hard_constraint", "rejected", "H3", "This crop needs irrigation; the field is recorded as rain-fed."
        )
    return None


@dataclass(frozen=True)
class RotationResult:
    result: CriterionResult
    seasons_needed: int  # how many of the most recent seasons the decision depends on


def rotation_soil(candidate_family: str, previous_families: list[str]) -> RotationResult:
    """R1-R3, exactly as the section 18 flowchart. previous_families is oldest first; gaps count as 'unknown'."""

    def result(label: str, rule: str | None, reason: str, needed: int) -> RotationResult:
        return RotationResult(CriterionResult("rotation_soil", label, rule, reason), needed)

    p1 = previous_families[-1] if previous_families else "unknown"
    p2 = previous_families[-2] if len(previous_families) >= 2 else "unknown"
    if candidate_family == "cereal":
        if p1 == "unknown":
            return result("insufficient_evidence", None, "the previous season's crop is unknown", 1)
        if p1 != "cereal":
            return result("mixed", "R3", "the run of cereal seasons is broken by the previous season", 1)
        if p2 == "unknown":
            return result("insufficient_evidence", None,
                          "a third cereal season in a row can be neither confirmed nor ruled out", 2)
        if p2 == "cereal":
            return result("concern", "R1", "at least 3 cereal seasons in a row", 2)
        return result("mixed", "R3", "only 2 cereal seasons in a row", 2)
    if candidate_family == "legume":
        if p1 == "unknown":
            return result("insufficient_evidence", None, "the previous season's crop is unknown", 1)
        if p1 == "cereal":
            return result("favorable", "R2", "a legume after a cereal season", 1)
        return result("mixed", "R3", "no specific rotation effect identified", 1)
    raise ValueError(f"no rotation rule covers a {candidate_family} candidate")


def water_fit(
    lower_need_mm: float | None, irrigation: str, site: SiteCheck, ind: Indicators
) -> CriterionResult:
    """R4 when every condition holds; otherwise R5 with every reason that applies."""
    blockers = []
    if site.result != "representative":
        blockers.append(site.reason)
    if irrigation != "rain-fed":
        blockers.append(f"irrigation is {irrigation}; the MVP measures rainfall only")
    if lower_need_mm is None:
        blockers.append("no confirmed water figure for this crop")
    if ind.baseline_mean_mm is None:
        blockers.append("baseline unavailable")
    if blockers:
        return CriterionResult("water_fit", "insufficient_evidence", "R5", "; ".join(blockers))

    n, total = seasons_meeting(ind, lower_need_mm)
    share = n / total
    label = "favorable" if share >= 0.80 else "mixed" if share >= 0.50 else "concern"
    return CriterionResult("water_fit", label, "R4", f"{n} of {total} baseline seasons reached {lower_need_mm:g} mm")


def rainfall_risk(ind: Indicators) -> CriterionResult:
    """R6: the same label for every plan at one location."""
    cv = ind.baseline_cv_pct
    if cv is None:
        return CriterionResult("risk", "insufficient_evidence", "R6", "baseline unavailable")
    label = "favorable" if cv < 20 else "mixed" if cv <= 35 else "concern"
    return CriterionResult("risk", label, "R6", f"seasonal rainfall varies by {cv:.1f}% (CV, 1991/92-2020/21)")
