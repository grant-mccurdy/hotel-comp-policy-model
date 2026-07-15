from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cloudflare.src.runtime_bundle import RUNTIME_POLICY_BUNDLE  # noqa: E402
from cloudflare.src.ui import DECISION_DESK_HTML  # noqa: E402
from scripts.build_runtime_policy_bundle import semantic_bundle_checksum  # noqa: E402


class WorkerAssetTests(unittest.TestCase):
    def test_generated_worker_bundle_matches_canonical_json(self) -> None:
        canonical = json.loads((PROJECT_ROOT / "config" / "runtime_policy_bundle.v1.json").read_text())
        self.assertEqual(RUNTIME_POLICY_BUNDLE, canonical)
        self.assertEqual(canonical["bundle_checksum"], semantic_bundle_checksum(canonical))

    def test_runtime_checksum_ignores_build_timestamp_but_not_policy_content(self) -> None:
        canonical = json.loads((PROJECT_ROOT / "config" / "runtime_policy_bundle.v1.json").read_text())
        changed_timestamp = deepcopy(canonical)
        changed_timestamp["source_generated_at"] = "2099-01-01T00:00:00+00:00"
        self.assertEqual(
            semantic_bundle_checksum(canonical),
            semantic_bundle_checksum(changed_timestamp),
        )
        changed_policy = deepcopy(canonical)
        changed_policy["policy"]["policy_version"] = "changed-version"
        self.assertNotEqual(
            semantic_bundle_checksum(canonical),
            semantic_bundle_checksum(changed_policy),
        )

    def test_generated_runtime_sources_match_canonical_modules(self) -> None:
        manifest = json.loads(
            (PROJECT_ROOT / "cloudflare" / "src" / "runtime_source_manifest.json").read_text()
        )
        for module_name, expected_hash in manifest["modules"].items():
            source = (PROJECT_ROOT / "scripts" / module_name).read_bytes()
            generated = (PROJECT_ROOT / "cloudflare" / "src" / "scripts" / module_name).read_bytes()
            self.assertEqual(generated, source)
            self.assertEqual(hashlib.sha256(source).hexdigest(), expected_hash)

    def test_worker_entry_is_valid_python(self) -> None:
        source = (PROJECT_ROOT / "cloudflare" / "src" / "entry.py").read_text()
        ast.parse(source)
        self.assertIn("/v1/recommend", source)
        self.assertIn("/v1/intake/parse", source)
        self.assertIn('body.get("scenario_mode", scenario.get("scenario_mode"))', source)
        self.assertIn('"json_schema": extraction_schema()', source)
        self.assertIn("fallback_incident_extraction(incident)", source)
        self.assertIn("merge_extraction_results(model_result, deterministic_result)", source)
        self.assertNotIn('"strict": True', source)

    def test_public_ui_exposes_decision_evidence_without_persistence(self) -> None:
        self.assertIn("Hotel Comp Decision Desk", DECISION_DESK_HTML)
        self.assertIn("Available recovery options", DECISION_DESK_HTML)
        self.assertIn("Closest feasible alternatives", DECISION_DESK_HTML)
        self.assertIn("do not enter names", DECISION_DESK_HTML)
        self.assertNotIn("localStorage", DECISION_DESK_HTML)

    def test_public_ui_explains_ambiguous_inputs_and_fallback(self) -> None:
        self.assertEqual(DECISION_DESK_HTML.count('class="field-term"'), 3)
        self.assertIn("Rate the failure itself, not guest emotion", DECISION_DESK_HTML)
        self.assertIn("negative public review or reputation issue", DECISION_DESK_HTML)
        self.assertIn("is not an abuse label", DECISION_DESK_HTML)
        self.assertIn("conservative text matches were applied", DECISION_DESK_HTML)
        self.assertIn("applySuggestedValue", DECISION_DESK_HTML)

    def test_public_wrangler_config_does_not_bind_shadow_database(self) -> None:
        config = (PROJECT_ROOT / "cloudflare" / "wrangler.toml").read_text()
        self.assertIn('SHADOW_LOGGING_ENABLED = "0"', config)
        self.assertNotIn("[[d1_databases]]", config)


if __name__ == "__main__":
    unittest.main()
