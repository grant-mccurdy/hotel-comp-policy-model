from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from decision_service import build_decision  # noqa: E402
from manager_app import DEFAULT_SCENARIO  # noqa: E402


class DecisionServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = json.loads((PROJECT_ROOT / "config" / "runtime_policy_bundle.v1.json").read_text())

    def scenario(self, **overrides: object) -> dict[str, object]:
        values: dict[str, object] = {
            **DEFAULT_SCENARIO,
            "guest_tier": "returning_guest",
            "stay_value": 1800,
            "estimated_lifetime_value": 7200,
            "nightly_rate": 600,
            "availability_confirmed": True,
        }
        values.update(overrides)
        return values

    def test_response_contract_is_complete_and_versioned(self) -> None:
        decision = build_decision(self.scenario(), self.bundle).as_dict()
        self.assertEqual(decision["schema_version"], "comp-decision-response-v1")
        self.assertEqual(decision["runtime_bundle_checksum"], self.bundle["bundle_checksum"])
        self.assertEqual(decision["policy_evidence"]["status"], "shadow_evaluation_candidate")
        self.assertIn(decision["confidence"]["level"], {"low", "moderate", "high"})
        self.assertEqual(len(decision["alternatives"]), 2)
        self.assertIn("hospitality_note_template", decision["recommendation"])

    def test_recommendation_respects_available_options(self) -> None:
        allowed = ["manager_note", "parking_fee_waiver", "partial_room_refund"]
        decision = build_decision(
            self.scenario(
                failure_category="valet_or_parking_delay",
                severity=3,
                available_comp_codes=allowed,
            ),
            self.bundle,
        )
        self.assertIn(decision.recommendation["comp_code"], allowed)
        self.assertTrue(all(item["comp_code"] in allowed for item in decision.alternatives))

    def test_guest_value_can_add_generosity_but_not_lower_failure_floor(self) -> None:
        low = build_decision(
            self.scenario(guest_tier="new_guest", stay_value=600, estimated_lifetime_value=0),
            self.bundle,
        )
        high = build_decision(
            self.scenario(guest_tier="vip_guest", stay_value=6000, estimated_lifetime_value=50000),
            self.bundle,
        )
        self.assertEqual(low.scenario["recovery_floor_score"], high.scenario["recovery_floor_score"])
        self.assertGreaterEqual(high.scenario["recovery_need_score"], low.scenario["recovery_need_score"])

    def test_repeat_comp_pattern_requires_review_without_changing_floor(self) -> None:
        baseline = build_decision(self.scenario(repeat_comp_review_risk=0.05), self.bundle)
        reviewed = build_decision(self.scenario(repeat_comp_review_risk=0.8), self.bundle)
        self.assertEqual(baseline.scenario["recovery_floor_score"], reviewed.scenario["recovery_floor_score"])
        self.assertTrue(reviewed.approval["manager_review_required"])
        self.assertFalse(reviewed.approval["repeat_comp_pattern_changes_recovery_floor"])


if __name__ == "__main__":
    unittest.main()
