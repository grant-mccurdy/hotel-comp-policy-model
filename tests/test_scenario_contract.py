from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scenario_contract import ScenarioInput, ScenarioValidationError  # noqa: E402


class ScenarioContractTests(unittest.TestCase):
    def base_mapping(self) -> dict[str, object]:
        return {
            "guest_tier": "loyalty_guest",
            "traveler_segment": "coastal_weekend",
            "stay_value": 2800,
            "estimated_lifetime_value": 14000,
            "nightly_rate": 700,
            "repeat_comp_review_risk": 0.04,
            "failure_category": "room_readiness_delay",
            "failure_type": "outcome",
            "severity": 4,
            "hotel_responsibility": 0.9,
            "reported_in_stay": True,
            "resolution_delay_minutes": 95,
            "sentiment_intensity": 0.76,
            "review_risk": 0.8,
            "occupancy_pressure": 0.72,
        }

    def test_valid_scenario_is_normalized(self) -> None:
        scenario = ScenarioInput.from_mapping(self.base_mapping())
        stay, failure = scenario.to_engine_inputs()
        self.assertEqual(stay["guest_tier"], "loyalty_guest")
        self.assertEqual(stay["repeat_comp_review_risk"], 0.04)
        self.assertEqual(failure["severity"], 4)
        self.assertGreater(stay["guest_value_score"], 0)

    def test_legacy_repeat_comp_alias_remains_readable(self) -> None:
        mapping = self.base_mapping()
        mapping.pop("repeat_comp_review_risk")
        mapping["repeat_comp_abuse_risk"] = 0.32
        scenario = ScenarioInput.from_mapping(mapping)
        self.assertEqual(scenario.repeat_comp_review_risk, 0.32)

    def test_impossible_values_are_rejected_together(self) -> None:
        mapping = self.base_mapping()
        mapping.update(
            {
                "stay_value": -1,
                "estimated_lifetime_value": -5,
                "hotel_responsibility": 8,
                "review_risk": -2,
                "occupancy_pressure": 4,
            }
        )
        with self.assertRaises(ScenarioValidationError) as context:
            ScenarioInput.from_mapping(mapping)
        self.assertEqual(
            set(context.exception.errors),
            {
                "stay_value",
                "estimated_lifetime_value",
                "hotel_responsibility",
                "review_risk",
                "occupancy_pressure",
            },
        )

    def test_unknown_categories_are_rejected(self) -> None:
        mapping = self.base_mapping()
        mapping["failure_category"] = "something_else"
        mapping["guest_tier"] = "platinum_unknown"
        with self.assertRaises(ScenarioValidationError) as context:
            ScenarioInput.from_mapping(mapping)
        self.assertIn("failure_category", context.exception.errors)
        self.assertIn("guest_tier", context.exception.errors)

    def test_severity_must_be_whole_number(self) -> None:
        mapping = self.base_mapping()
        mapping["severity"] = 3.5
        with self.assertRaises(ScenarioValidationError) as context:
            ScenarioInput.from_mapping(mapping)
        self.assertIn("whole number", context.exception.errors["severity"])


if __name__ == "__main__":
    unittest.main()
