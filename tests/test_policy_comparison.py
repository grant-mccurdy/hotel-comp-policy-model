from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from common import (  # noqa: E402
    POLICY_CASE_COMPARISON_PATH,
    POLICY_DECISION_SUMMARY_PATH,
    RECOVERY_CASE_MART_PATH,
    read_csv_rows,
)
from evaluate_policy_strategies import (  # noqa: E402
    baseline_selection,
    build_case_policy_rows,
    build_segment_rows,
    probabilistic_sensitivity,
    recommend_policy_strategy,
    select_pilot_policy,
)
from manager_app import DEFAULT_SCENARIO  # noqa: E402
from policy_config import comp_catalog, load_policy_config, load_policy_scenarios  # noqa: E402


class PolicyComparisonTests(unittest.TestCase):
    def test_generated_comparison_has_complete_unique_grain(self) -> None:
        _, case_rows = read_csv_rows(POLICY_CASE_COMPARISON_PATH)
        _, summary_rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
        keys = {(row["recovery_case_id"], row["policy_id"]) for row in case_rows}
        case_ids = {row["recovery_case_id"] for row in case_rows}
        policy_ids = {row["policy_id"] for row in summary_rows}
        self.assertEqual(len(policy_ids), 5)
        self.assertEqual(len(case_ids), 430)
        self.assertEqual(len(case_rows), len(keys))
        self.assertEqual(len(case_rows), len(case_ids) * len(policy_ids))

    def test_pilot_selection_is_generated_not_hardcoded(self) -> None:
        config = load_policy_scenarios()
        policy_ids = [row["policy_id"] for row in config["policies"]]
        metrics = {
            policy_id: {"direct_room_refund_value": 100.0, "manager_review_rate": 0.2}
            for policy_id in policy_ids
        }
        uncertainty = [
            {
                "policy_id": policy_id,
                "joint_guardrail_pass_probability": 0.95 if policy_id == "recovery_first" else 0.0,
                "internal_cost_p50": 1000 + index,
            }
            for index, policy_id in enumerate(policy_ids)
        ]
        selected, recommendation = select_pilot_policy(metrics, uncertainty, config)
        self.assertEqual(selected, "recovery_first")
        self.assertIn("Recovery first", recommendation)

    def test_missing_baseline_comp_is_unknown(self) -> None:
        policy = load_policy_config()
        catalog = {row["comp_code"]: row for row in comp_catalog(policy)}
        result = baseline_selection(
            {"actual_comp_codes_normalized": "", "actual_comp_face_value": "", "actual_comp_internal_cost": ""},
            3,
            catalog,
            policy,
        )
        self.assertEqual(result["comp_code"], "no_matched_comp_record")
        self.assertFalse(result["adequacy_evaluable"])

    def test_small_segment_metrics_are_suppressed(self) -> None:
        _, case_rows = read_csv_rows(POLICY_CASE_COMPARISON_PATH)
        sample = [row for row in case_rows if row["policy_id"] == "cost_guardrail"][:5]
        segments = build_segment_rows(sample, load_policy_scenarios())
        self.assertTrue(segments)
        for row in segments:
            self.assertEqual(row["suppressed_small_group"], "true")
            self.assertEqual(row["adequacy_rate"], "")
            self.assertEqual(row["internal_cost_mid"], "")

    def test_after_checkout_manager_scenario_cannot_offer_room_gesture(self) -> None:
        scenario = dict(DEFAULT_SCENARIO, reported_in_stay="false")
        result = recommend_policy_strategy(scenario, "cost_guardrail")
        self.assertNotIn(result["comp_code"], {"room_upgrade", "late_checkout"})

    def test_sensitivity_results_do_not_depend_on_policy_iteration_order(self) -> None:
        policy = load_policy_config()
        config = deepcopy(load_policy_scenarios())
        config["probabilistic_sensitivity"]["draws"] = 40
        _, cases = read_csv_rows(RECOVERY_CASE_MART_PATH)
        case_rows = build_case_policy_rows(cases, config, policy)
        rows_by_policy: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in case_rows:
            rows_by_policy[str(row["policy_id"])].append(row)
        cases_by_id = {row["recovery_case_id"]: row for row in cases}

        forward, _ = probabilistic_sensitivity(dict(rows_by_policy), cases_by_id, config, policy)
        reversed_order, _ = probabilistic_sensitivity(
            dict(reversed(list(rows_by_policy.items()))), cases_by_id, config, policy
        )

        def comparable(rows: list[dict[str, object]]) -> dict[str, tuple[object, ...]]:
            return {
                str(row["policy_id"]): (
                    row["joint_guardrail_pass_probability"],
                    row["internal_cost_p05"],
                    row["internal_cost_p50"],
                    row["internal_cost_p95"],
                    row["policy_selection_probability"],
                )
                for row in rows
            }

        self.assertEqual(comparable(forward), comparable(reversed_order))


if __name__ == "__main__":
    unittest.main()
