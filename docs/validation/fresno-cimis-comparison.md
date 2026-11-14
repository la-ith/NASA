# Fresno CIMIS development comparison

Live CIMIS access succeeded. No model parameters or source observations were changed.

| Year | Paired days / 153 | ET0 bias mm/day | RMSE mm/day | Paired-total difference | Meets 95% paired-day threshold |
|---|---:|---:|---:|---:|---|
| 2020 | 145 | 0.692 | 1.098 | 10.4% | False |
| 2021 | 149 | 0.868 | 1.145 | 12.8% | True |
| 2022 | 152 | 0.436 | 0.890 | 6.0% | True |

NASA-driven ET0 exceeds the quality-screened station reference on average in each evaluated year. The paired comparison does not prove a unique cause or a correction for the 25-season irrigation median.

Totals use only paired valid days and are not full-season observations or extrapolations. In 2020, 145/153 days are below the preselected 146-day threshold; that year remains a diagnostic comparison.

## Quality and spatial support

- Only unflagged reference values are retained; QA exclusions can change the comparison sample.
- Current station is grass/ETo-designated; siting notes dated 2002 mention variable grass height and dust. Historical maintenance conditions need review.
- CIMIS published ASCE ETo and daily FAO-56 use related reference methods but are not an exact equation-identity test.
- These development years and station are distinct from the consumed frozen holdout study. No parameters are fitted.
- A station-reference comparison does not measure crop ET, yield or actual field irrigation.

Component bias/MAE/RMSE and original source artifacts are retained in results/fresno-cimis-comparison.json. Component comparisons can use different QA-valid day subsets; do not treat their biases as a formal causal decomposition.

The station is an irrigated grass/pasture reference site; NASA POWER represents regional grid conditions. Warmer/drier regional inputs can produce higher reference ET0 than locally irrigated station inputs. This is an interpretation consistent with the inputs, not an identified sole cause.

Remaining: assess local climate support, crop calendar, initial moisture and management against actual field observations. Published reference ET0 is not measured maize ET or irrigation use.
