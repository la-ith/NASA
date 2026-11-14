# Frozen holdout evaluation v1

Engineering weather screening: **not_qualified**.
Field irrigation accuracy is not validated. Expert agronomic review remains pending. No model parameters were tuned.

| Group | Station | Year | ET0 bias mm/day | RMSE mm/day | Gate |
|---|---|---|---:|---:|---|
| temporal_holdout | az06 | 2023 | 0.272 | 0.844 | failed |
| temporal_holdout | az06 | 2024 | 0.102 | 0.744 | failed |
| temporal_holdout | az06 | 2025 | 0.084 | 0.825 | failed |
| temporal_holdout | ftc01 | 2023 | 1.208 | 1.474 | failed |
| temporal_holdout | ftc01 | 2024 | 1.243 | 1.472 | failed |
| temporal_holdout | ftc01 | 2025 | 1.388 | 1.581 | failed |
| temporal_holdout | hays | 2023 | 0.089 | 0.835 | failed |
| temporal_holdout | hays | 2024 | 0.008 | 0.821 | passed |
| temporal_holdout | hays | 2025 | 0.118 | 0.942 | passed |
| spatial_holdout | az01 | 2020 | 1.360 | 1.662 | failed |
| spatial_holdout | az01 | 2021 | 0.966 | 1.300 | failed |
| spatial_holdout | az01 | 2022 | 0.972 | 1.337 | failed |
| spatial_holdout | akr02 | 2020 | -0.150 | 0.878 | passed |
| spatial_holdout | akr02 | 2021 | 0.186 | 0.822 | failed |
| spatial_holdout | akr02 | 2022 | -0.203 | 2.593 | failed |
| spatial_holdout | gly04 | 2020 | 1.068 | 1.352 | failed |
| spatial_holdout | gly04 | 2021 | 1.450 | 2.088 | failed |
| spatial_holdout | gly04 | 2022 | 0.873 | 1.123 | failed |
| spatial_holdout | colby | 2020 | 0.689 | 0.970 | failed |
| spatial_holdout | colby | 2021 | 0.413 | 0.850 | passed |
| spatial_holdout | colby | 2022 | 0.196 | 0.707 | failed |

Gates are provisional product screening limits fixed before opening data, not published guarantees. FTC01 is diagnostic-only because of known siting concerns. See JSON for missingness, failed gates, paired-season totals, block-bootstrap intervals and source hashes.

These evaluation groups are now consumed. After any parameter tuning, use fresh untouched data for a new final evaluation.
