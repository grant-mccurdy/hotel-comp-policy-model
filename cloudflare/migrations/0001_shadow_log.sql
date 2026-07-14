-- Defined for a future Access-protected shadow environment.
-- The public synthetic demo does not bind D1 or execute these writes.
CREATE TABLE decision_cases (
  decision_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  environment TEXT NOT NULL CHECK (environment = 'authenticated_shadow_evaluation'),
  schema_version TEXT NOT NULL,
  runtime_bundle_version TEXT NOT NULL,
  runtime_bundle_checksum TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  scenario_json TEXT NOT NULL,
  recommendation_json TEXT NOT NULL
);

CREATE TABLE decision_events (
  event_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('accepted', 'modified', 'overridden', 'delivered')),
  selected_comp_code TEXT,
  selected_guest_facing_value REAL,
  override_reason_code TEXT,
  override_note TEXT,
  actor_subject TEXT NOT NULL,
  FOREIGN KEY (decision_id) REFERENCES decision_cases(decision_id)
);

CREATE TABLE outcome_events (
  outcome_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  post_recovery_satisfaction REAL,
  resolution_minutes REAL,
  actual_marginal_cost REAL,
  public_review_flag INTEGER CHECK (public_review_flag IN (0, 1) OR public_review_flag IS NULL),
  repeat_stay_flag INTEGER CHECK (repeat_stay_flag IN (0, 1) OR repeat_stay_flag IS NULL),
  outcome_window_days INTEGER,
  FOREIGN KEY (decision_id) REFERENCES decision_cases(decision_id)
);

CREATE INDEX idx_decision_events_decision_id ON decision_events(decision_id);
CREATE INDEX idx_outcome_events_decision_id ON outcome_events(decision_id);
