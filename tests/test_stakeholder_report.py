from __future__ import annotations

import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from stakeholder_report import build_scenario_presentations, render_stakeholder_page  # noqa: E402


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            self.parts.append(data)

    @property
    def word_count(self) -> int:
        return len(" ".join(self.parts).split())


class StakeholderReportTests(unittest.TestCase):
    def test_page_leads_with_shadow_validation_decision(self) -> None:
        page = render_stakeholder_page()
        self.assertIn("Comp Policy Shadow-Validation Decision", page)
        self.assertIn("Executive decision", page)
        self.assertIn("Why Guardrailed Recovery advances", page)
        self.assertIn("Five policies were tested", page)
        self.assertIn("Shadow first, manager-assisted test second", page)
        self.assertIn("Guardrailed recovery", page)
        self.assertIn("Engineering evidence", page)
        self.assertIn("not observed Proper Hotels performance or projected savings", page)
        self.assertNotIn("portfolio", page.lower())

    def test_decision_figure_explains_selection_rule(self) -> None:
        page = render_stakeholder_page()
        self.assertEqual(page.count('class="policy-plot-row '), 5)
        self.assertIn("How to read", page)
        self.assertIn("5th–95th percentile modeled-cost range", page)
        self.assertIn("lowest median cost among qualifiers", page)
        self.assertIn("Median $30.5K · range $27.3K–$33.9K", page)
        self.assertIn("99.6% pass", page)
        self.assertIn("not projected savings", page)

    def test_page_remains_a_concise_executive_brief(self) -> None:
        parser = VisibleTextParser()
        parser.feed(render_stakeholder_page())
        self.assertGreaterEqual(parser.word_count, 400)
        self.assertLessEqual(parser.word_count, 650)

    def test_worked_scenarios_are_complete(self) -> None:
        scenarios = build_scenario_presentations()
        self.assertEqual(len(scenarios), 4)
        self.assertEqual(scenarios[0]["key"], "arrival_delay")
        for scenario in scenarios:
            self.assertTrue(scenario["amount"])
            self.assertTrue(scenario["gesture"])
            self.assertTrue(scenario["cost_range"])
            self.assertTrue(scenario["reasons"])
            self.assertIn(scenario["approval"], {"Manager approval", "Within policy"})

    def test_primary_example_is_manager_ready(self) -> None:
        example = build_scenario_presentations()[0]
        self.assertEqual(example["amount"], "$240")
        self.assertIn("partial room refund", str(example["gesture"]))
        self.assertEqual(example["approval"], "Manager approval")
        self.assertIn("room availability", str(example["counterfactual"]))

    def test_supporting_reports_can_use_the_same_canonical_example(self) -> None:
        example = build_scenario_presentations()[0]
        self.assertEqual(example["cost_range"], "$240-$240")
        self.assertIn("manager note", str(example["gesture"]))
        self.assertIn("assumption-stress draws", str(example["robustness"]))


if __name__ == "__main__":
    unittest.main()
