"""Transparent within-analysis water-gap scores (not crop-failure probabilities)."""


def summarize_water_stress(strategies: list[dict]) -> None:
    """Attach a relative deficit score and descriptive historical exposure count.

    The score is each crop's median seasonal rain-fed deficit divided by the largest
    median deficit among options in this comparison. It is a within-analysis index,
    not a probability, forecast, validated agronomic risk score, or suitability rating.
    """
    raw = []
    for strategy in strategies:
        seasons = strategy.get("result", {}).get("seasons", [])
        eligible = [s for s in seasons if s.get("rainfed_stress_days") is not None]
        affected = [s for s in eligible if s["rainfed_stress_days"] > 0]
        percentage = round(100 * len(affected) / len(eligible), 1) if eligible else None
        deficit = strategy.get("result", {}).get("summary", {}).get("rainfed_deficit", {}).get("spread")
        raw.append((strategy, len(affected), len(eligible), percentage, deficit))

    deficits = [item[4].get("median") for item in raw if item[4] and item[4].get("median") is not None]
    max_deficit = max(deficits) if deficits else None
    scores = [round(max(0, float(item[4]["median"])) / max_deficit * 100, 1)
              if item[4] and item[4].get("median") is not None and max_deficit and max_deficit > 0
              else (0.0 if item[4] and item[4].get("median") is not None else None)
              for item in raw]
    known = [score for score in scores if score is not None]
    low = min(known) if known else None
    high = max(known) if known else None
    for (strategy, affected, assessed, historical_pct, deficit), score in zip(raw, scores):
        if score is None:
            level = "insufficient_data"
            factor = "Not enough valid simulated seasons to assess water stress."
            median_deficit = None
        else:
            median_deficit = deficit.get("median") if deficit else None
            if low == high or score == low == high:
                level = "similar"
            elif score == low:
                level = "lower"
            elif score == high:
                level = "higher"
            else:
                level = "middle"
            if median_deficit is None:
                factor = "Rain-fed water deficit could not be calculated for this crop."
            elif median_deficit >= 0:
                factor = f"Median modeled rain-fed water deficit: {median_deficit:.1f} mm per season. This combines crop demand, past weather, and mapped soil storage."
            else:
                factor = "No median rain-fed water deficit in the simulated seasons."
        strategy["water_stress_exposure"] = {
            "label": "Relative water-gap score",
            "percentage": score,
            "relative_score_pct": score,
            "comparison_max_deficit_mm": max_deficit,
            "seasons_affected": affected,
            "seasons_assessed": assessed,
            "historical_exposure_pct": historical_pct,
            "relative_level": level,
            "primary_contributing_factor": factor,
            "median_rainfed_deficit_mm": median_deficit,
            "definition": "Crop median rain-fed deficit divided by the largest crop median deficit in this comparison, times 100.",
            "interpretation": "Relative historical model index for these options only, not a probability of crop failure or a forecast.",
        }
