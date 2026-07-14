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
    def test_page_follows_an_executive_data_story_arc(self) -> None:
        page = render_stakeholder_page()
        self.assertIn("Which Comp Policy Should Enter Shadow Validation?", page)
        self.assertIn("Executive answer", page)
        self.assertIn("Guardrailed recovery", page)
        narrative_markers = [
            "Operating context",
            "A room delay forces a choice before the full cost is known",
            "The cheapest synthetic comparator fails the modeled adequacy test",
            "Policy comparison",
            "Three policies clear the modeled guardrails; Guardrailed Recovery has the lowest modeled cost",
            "Manager application",
            "The selected policy turns the opening case into a manager-ready choice",
            "Controlled validation",
            "The next decision is whether the rule survives real operations",
            "Methods and engineering evidence",
        ]
        positions = [page.index(marker) for marker in narrative_markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("candidate selection for shadow validation, not policy adoption", page)
        self.assertIn("do not estimate Proper Hotels performance or savings", page)
        self.assertNotIn("protect the guest", page.lower())
        self.assertNotIn("guest-protection test", page.lower())
        self.assertNotIn("portfolio", page.lower())

    def test_opening_case_returns_after_the_policy_climax(self) -> None:
        page = render_stakeholder_page()
        opening = page.index("<strong>Room not ready at arrival.</strong>")
        climax = page.index('class="policy-decision-figure"')
        resolution = page.index('<h3 id="scenario-title">Room not ready at arrival</h3>')
        self.assertLess(opening, climax)
        self.assertLess(climax, resolution)
        self.assertIn("$240", page[resolution:])
        self.assertIn("partial room refund + manager note", page[resolution:])

    def test_decision_figure_explains_protection_then_cost(self) -> None:
        page = render_stakeholder_page()
        self.assertEqual(page.count('class="policy-plot-row '), 5)
        self.assertEqual(page.count('class="protection-cell"'), 5)
        self.assertIn("How to read", page)
        self.assertIn("Adequate or reviewed", page)
        self.assertIn("Inadequate and unreviewed", page)
        self.assertIn("cost P05–P95", page)
        self.assertIn("before cost comparison", page)
        self.assertIn("Median $30.5K · range $27.3K–$33.9K", page)
        self.assertIn("99.6% pass", page)
        self.assertIn("Not projected savings", page)
        self.assertIn("Source:</strong> synthetic policy mart, 430 cases", page)
        self.assertIn('href="reports/methodology-and-assumptions.md"', page)
        self.assertIn('href="reports/policy-sensitivity.md"', page)

    def test_page_remains_a_concise_executive_brief(self) -> None:
        parser = VisibleTextParser()
        parser.feed(render_stakeholder_page())
        self.assertGreaterEqual(parser.word_count, 650)
        self.assertLessEqual(parser.word_count, 800)

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
        self.assertIn("Policy clears all modeled guardrails", str(example["robustness"]))

    def test_supporting_reports_can_use_the_same_canonical_example(self) -> None:
        example = build_scenario_presentations()[0]
        self.assertEqual(example["cost_range"], "$240-$240")
        self.assertIn("manager note", str(example["gesture"]))
        self.assertIn("shared stress draws", str(example["robustness"]))


if __name__ == "__main__":
    unittest.main()
