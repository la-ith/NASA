"""Plain-language text built from engine results (section 18 templates). Deterministic: no generative AI (decision 9)."""
from app.domain.rules import CriterionResult
from app.services.climate_context import ClimateContext
from app.services.indicators import BASELINE_YEARS, season_label, seasons_meeting
from app.services.validation import PARAMETER

BASELINE_SPAN = f"{season_label(BASELINE_YEARS[0])}–{season_label(BASELINE_YEARS[-1])}"
CRITERION_ORDER = {  # section 7: the goal orders criteria and picks the summary; it never changes a label
    "conserve_water": ["water_fit", "risk", "rotation_soil"],
    "improve_soil_rotation": ["rotation_soil", "water_fit", "risk"],
    "balance_both": ["water_fit", "rotation_soil", "risk"],
}
CRITERION_NAME = {"rotation_soil": "Rotation/soil", "water_fit": "Water fit", "risk": "Risk"}
LABEL_TEXT = {"favorable": "favorable", "mixed": "mixed", "concern": "a concern",
              "insufficient_evidence": "insufficient evidence"}
NOTICE = (
    "Field Shift compares options using the information and sources shown. Gridded climate data may not represent "
    "conditions within your exact field, and historical conditions do not predict next season. Review choices with "
    "local agricultural expertise."
)
LOCAL_QUESTIONS = [
    "Is rainfall at your field closer to the Hebron station record or to the regional value shown?",
    "Is there a buyer or a use for lentil or vetch near you, and at what price?",
    "Are seed and suitable harvesting equipment available for the alternative crop?",
    "What has your agricultural extension officer seen with these rotations locally?",
]
ACKNOWLEDGEMENT = (
    "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's "
    "Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division."
)


def _rule(code: str, state: str) -> str:
    return f"Draft rule {code}" if state != "reviewed" else f"Rule {code}"


def _status(state: str) -> str:
    return "Rule status: reviewed." if state == "reviewed" else "Rule status: not yet reviewed."


def insufficient(criterion_name: str, reason: str) -> str:
    return f"We could not assess {criterion_name} for this plan, because {reason}. This is not a negative result."


def rotation(r: CriterionResult, crop: str, history: list[tuple[str, str]], state: str) -> str:
    season1, crop1 = history[-1]
    season2 = history[-2][0] if len(history) >= 2 else season_label(int(season1[:4]) - 1)
    if r.rule == "R1":
        return (f"This plan would make at least 3 cereal seasons in a row on this field ({season2}, {season1}, and "
                f"next season). {_rule('R1', state)} flags this as a rotation concern. {_status(state)}")
    if r.rule == "R2":
        return (f"{crop.capitalize()} is a legume following a cereal ({season1}: {crop1}). "
                f"{_rule('R2', state)} marks this as a rotation benefit. {_status(state)}")
    if r.rule == "R3":
        return (f"No specific rotation effect was identified for {crop} after {crop1} ({season1}): {r.reason}. "
                f"{_status(state)}")
    return insufficient("rotation/soil", r.reason)


def water(r: CriterionResult, crop: str, lower_need_mm: float | None, climate: ClimateContext) -> str:
    site = climate.site
    if r.rule == "R4":
        n, total = seasons_meeting(climate.indicators, lower_need_mm)
        return (f"In {n} of {total} past seasons ({BASELINE_SPAN}), rainfall for this area reached "
                f"{lower_need_mm:g} mm, the lower FAO indicative water need for {crop}. Area data comes from one "
                f"NASA POWER grid cell and was checked against {site.station_name} station.")
    if site.result == "not_representative":
        others = [b for b in r.reason.split("; ") if b != site.reason]
        text = (f"We could not assess water fit, because the NASA POWER area average ({site.cell_mean_mm:.1f} mm per "
                f"season) differs too much from the local station record ({site.station_mean_mm:.1f} mm). "
                "This is not a negative result.")
        return text + (f" Also: {'; '.join(others)}." if others else "")
    return insufficient("water fit", r.reason)


def risk(r: CriterionResult, climate: ClimateContext) -> str:
    if r.label == "insufficient_evidence":
        return insufficient("risk", r.reason)
    return (f"Rainfall in this area varied by {climate.indicators.baseline_cv_pct:.1f}% from season to season "
            f"({BASELINE_SPAN}). Team cut-offs: under 20% favorable, 20–35% mixed, over 35% concern. "
            "This describes the area, not the crop.")


def inputs(
    history: list[tuple[str, str]], field: dict, crop: str, lower_need_mm: float | None,
    water_source: str | None, seasons_needed: int, climate: ClimateContext,
) -> list[dict]:
    """The "What we know" panel (section 7): each decision-relevant input as entered, estimated, assumed or missing."""
    recorded = dict(history)
    last_year = int(history[-1][0][:4])
    first_needed = last_year - seasons_needed + 1
    items = []
    for year in range(min(int(history[0][0][:4]), first_needed), last_year + 1):
        label, value = season_label(year), recorded.get(season_label(year))
        needed = year >= first_needed
        if value in (None, "unknown"):
            effect = ("Needed by the rotation/soil rule, so that criterion has insufficient evidence." if needed
                      else "Not needed for this plan's rotation check.")
            items.append({"name": f"crop {label}", "state": "missing",
                          "source": "not entered" if value is None else "farmer: unknown", "effect": effect})
        elif value == "other":
            effect = ("Its crop type is not classified, so rotation/soil has insufficient evidence." if needed
                      else "Not needed for this plan's rotation check.")
            items.append({"name": f"crop {label}", "state": "entered", "source": "farmer: other crop", "effect": effect})
        else:
            effect = "Used by the rotation/soil rule." if needed else "Not needed for this plan's rotation check."
            items.append({"name": f"crop {label}", "state": "entered", "source": f"farmer: {value}", "effect": effect})

    irrigation = field["irrigation"]
    irrigation_effect = {
        "rain-fed": "Water fit compares rainfall with the crop's need.",
        "unknown": "Water fit cannot be assessed without it.",
    }.get(irrigation, "Water fit cannot be assessed: irrigation water is not measured in this version.")
    items.append({"name": "irrigation", "state": "missing" if irrigation == "unknown" else "entered",
                  "source": f"farmer: {irrigation}", "effect": irrigation_effect})
    soil = field["soil"]
    items.append({"name": "soil type", "state": "missing" if soil == "unknown" else "entered",
                  "source": f"farmer: {soil}", "effect": "Shown as context; no rule in this version uses it."})
    start, end = climate.period
    items.append({"name": "seasonal rainfall", "state": "estimated",
                  "source": f"NASA POWER {PARAMETER}, one grid cell of about 56 km × 59 km, {start} to {end}",
                  "effect": f"Regional value. Site check: {climate.site.reason}."})
    items.append({"name": f"{crop} water need",
                  "state": "missing" if lower_need_mm is None else "entered",
                  "source": f"team: {water_source}" if lower_need_mm is not None else "no confirmed figure",
                  "effect": ("Water fit has insufficient evidence; no other crop's figure is borrowed."
                             if lower_need_mm is None else f"Lower bound {lower_need_mm:g} mm used by water fit.")})
    return items


def summary(goal: str, plans: list[dict]) -> str:
    """Names the highest-priority criterion on which plans differ, and any criterion no plan could be assessed on."""
    evaluated = [p for p in plans if p["status"] == "evaluated"]
    order = CRITERION_ORDER[goal]
    labels = {c: [(p, next(x["label"] for x in p["criteria"] if x["criterion"] == c)) for p in evaluated] for c in order}
    parts = []
    for c in order:
        if len({label for _, label in labels[c]}) > 1:
            listed = "; ".join(
                f"{p['crop']}{' (current practice)' if p['type'] == 'current_practice' else ''} is {LABEL_TEXT[label]}"
                for p, label in labels[c]
            )
            parts.append(f"{CRITERION_NAME[c]} differs: {listed}.")
            break
    else:
        parts.append("The plans do not differ on any criterion that could be assessed.")
    parts += [f"{CRITERION_NAME[c]} could not be assessed for any plan." for c in order
              if evaluated and all(label == "insufficient_evidence" for _, label in labels[c])]
    return " ".join(parts)


def limitations(climate: ClimateContext, illustrative: bool) -> list[str]:
    items = ["Gridded rainfall is regional context, not a measurement at your field.",
             "Historical conditions do not predict next season."]
    if climate.site.result != "representative":
        items.append(f"Water fit was not assessed: {climate.site.reason}.")
    if illustrative:
        items.append("The rules are illustrative and have not yet been reviewed by an agricultural specialist.")
    if climate.mode == "sample":
        items.append("This analysis uses the saved sample record, not a live NASA call.")
    if climate.record.flags:
        items.append(f"{len(climate.record.flags)} daily value(s) were flagged for review and kept unchanged.")
    return items


def data_reference(climate: ClimateContext) -> str:
    version = climate.record.api_version.removeprefix("v")
    return f"The data was obtained from the POWER Project's Daily {version} version on {climate.retrieved_utc:%Y/%m/%d}."
