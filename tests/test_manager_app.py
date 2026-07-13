from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from manager_app import DEFAULT_SCENARIO, params_from_query, render_page, scenario_to_recommendation  # noqa: E402
from scenario_contract import ScenarioValidationError  # noqa: E402


class ManagerAppTests(unittest.TestCase):
    def test_default_page_contains_decision_evidence(self) -> None:
        page = render_page(dict(DEFAULT_SCENARIO))
        self.assertIn("Recommended recovery", page)
        self.assertIn("Closest alternatives", page)
        self.assertIn("What must be confirmed", page)
        self.assertIn("Estimated internal cost", page)
        self.assertIn("Guardrailed recovery", page)

    def test_preset_is_loaded(self) -> None:
        params = params_from_query("preset=parking_friction")
        self.assertEqual(params["failure_category"], "valet_or_parking_delay")
        _, recommendation = scenario_to_recommendation(params)
        self.assertEqual(recommendation.comp_code, "parking_fee_waiver")
        self.assertEqual(recommendation.policy_id, "cost_guardrail")

    def test_invalid_query_is_rejected(self) -> None:
        params = params_from_query("stay_value=-1&hotel_responsibility=4")
        with self.assertRaises(ScenarioValidationError):
            scenario_to_recommendation(params)


if __name__ == "__main__":
    unittest.main()
