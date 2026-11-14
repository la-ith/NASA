-- Crop profiles and rule set 0.1 from section 18. Every row starts as draft-unreviewed.
-- Supported candidate crops have season 'winter'; history-only choices have season NULL.
INSERT INTO crop (name, crop_type, season, water_need_min_mm, water_need_max_mm, water_source, review_state)
VALUES
  ('wheat',    'cereal',        'winter', 450, 650, 'FAO Irrigation Water Management Training Manual No. 3, Table 14', 'draft-unreviewed'),
  ('lentil',   'grain_legume',  'winter', NULL, NULL, NULL, 'draft-unreviewed'),
  ('vetch',    'forage_legume', 'winter', NULL, NULL, NULL, 'draft-unreviewed'),
  ('barley',   'cereal',        NULL,     NULL, NULL, NULL, 'draft-unreviewed'),
  ('chickpea', 'grain_legume',  NULL,     NULL, NULL, NULL, 'draft-unreviewed'),
  ('fallow',   'fallow',        NULL,     NULL, NULL, NULL, 'draft-unreviewed'),
  ('other',    'unclassified',  NULL,     NULL, NULL, NULL, 'draft-unreviewed')
ON CONFLICT DO NOTHING;

INSERT INTO rotation_rule (code, version, condition, effect, citation, region, reviewer, review_state)
VALUES
  ('H1', '0.1', 'candidate crop is not in the supported candidate list', 'reject plan', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('H2', '0.1', 'candidate profile season differs from the candidate season', 'reject plan', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('H3', '0.1', 'candidate is irrigated-only and the field is rain-fed', 'reject plan', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R1', '0.1', 'cereal candidate after two cereal seasons', 'rotation_soil: concern', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R2', '0.1', 'legume candidate after a cereal season', 'rotation_soil: favorable', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R3', '0.1', 'neither R1 nor R2 applies and history is sufficient', 'rotation_soil: mixed', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R4', '0.1', 'site check representative, field rain-fed, confirmed lower water need T, baseline available',
   'water_fit: share of baseline seasons >= T: 80% or more favorable, 50% to under 80% mixed, under 50% concern',
   'FAO Irrigation Water Management Training Manual No. 3, Table 14', 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R5', '0.1', 'any R4 condition not met', 'water_fit: insufficient evidence', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed'),
  ('R6', '0.1', 'baseline coefficient of variation', 'risk: under 20% favorable, 20% to 35% mixed, over 35% concern', NULL, 'Hebron pilot area', NULL, 'draft-unreviewed')
ON CONFLICT DO NOTHING;
