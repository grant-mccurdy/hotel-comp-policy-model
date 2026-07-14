from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    from .common import (
        CLOUDFLARE_RUNTIME_BUNDLE_MODULE_PATH,
        CLOUDFLARE_RUNTIME_SOURCE_DIR,
        CLOUDFLARE_RUNTIME_SOURCE_MANIFEST_PATH,
        PROJECT_ROOT,
        POLICY_COMPARISON_MANIFEST_PATH,
        POLICY_DECISION_SUMMARY_PATH,
        RUNTIME_POLICY_BUNDLE_PATH,
        read_csv_rows,
        read_json,
        write_json,
    )
    from .policy_config import load_policy_config, load_policy_scenarios
except ImportError:
    from common import (
        CLOUDFLARE_RUNTIME_BUNDLE_MODULE_PATH,
        CLOUDFLARE_RUNTIME_SOURCE_DIR,
        CLOUDFLARE_RUNTIME_SOURCE_MANIFEST_PATH,
        PROJECT_ROOT,
        POLICY_COMPARISON_MANIFEST_PATH,
        POLICY_DECISION_SUMMARY_PATH,
        RUNTIME_POLICY_BUNDLE_PATH,
        read_csv_rows,
        read_json,
        write_json,
    )
    from policy_config import load_policy_config, load_policy_scenarios


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def semantic_bundle_checksum(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("bundle_checksum", None)
    payload.pop("source_generated_at", None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_bundle() -> dict[str, Any]:
    _, rows = read_csv_rows(POLICY_DECISION_SUMMARY_PATH)
    selected = next(
        (
            row
            for row in rows
            if row.get("selected_for_shadow_evaluation", row.get("selected_for_pilot", "")) == "true"
        ),
        None,
    )
    if selected is None:
        raise RuntimeError("No policy cleared the declared shadow-evaluation guardrails.")

    manifest = read_json(POLICY_COMPARISON_MANIFEST_PATH)
    payload = {
        "schema_version": "comp-runtime-bundle-v1",
        "bundle_version": "comp-decision-runtime-v1.0.0",
        "source_generated_at": manifest["generated_at"],
        "evidence_class": "synthetic_workflow_demonstration",
        "allowed_modes": ["public_synthetic_demo", "authenticated_shadow_evaluation"],
        "selection": {
            "policy_id": selected["policy_id"],
            "policy_label": selected["policy_label"],
            "policy_strategy": selected["policy_strategy"],
            "cases": int(float(selected["cases"])),
            "joint_guardrail_pass_probability": float(selected["joint_guardrail_pass_probability"]),
            "executive_recommendation": selected["executive_recommendation"],
        },
        "policy": load_policy_config(),
        "scenario_config": load_policy_scenarios(),
        "source_manifest": {
            "comparison_version": manifest["comparison_version"],
            "case_count": manifest["case_count"],
            "sensitivity_draws": manifest["sensitivity_draws"],
            "outcome_boundary": manifest["outcome_boundary"],
        },
    }
    payload["bundle_checksum"] = semantic_bundle_checksum(payload)
    return payload


def write_python_module(bundle: dict[str, Any]) -> None:
    CLOUDFLARE_RUNTIME_BUNDLE_MODULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=True)
    module = (
        '"""Generated runtime policy bundle. Rebuild with `make runtime-bundle`."""\n\n'
        "import json\n\n"
        f"RUNTIME_POLICY_BUNDLE = json.loads(r'''{serialized}''')\n"
    )
    CLOUDFLARE_RUNTIME_BUNDLE_MODULE_PATH.write_text(module, encoding="utf-8")


def write_runtime_sources() -> None:
    module_names = [
        "__init__.py",
        "common.py",
        "decision_service.py",
        "evaluate_policy_strategies.py",
        "intake_contract.py",
        "policy_config.py",
        "policy_engine.py",
        "scenario_contract.py",
    ]
    CLOUDFLARE_RUNTIME_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    for module_name in module_names:
        source = PROJECT_ROOT / "scripts" / module_name
        destination = CLOUDFLARE_RUNTIME_SOURCE_DIR / module_name
        content = source.read_bytes()
        destination.write_bytes(content)
        checksums[module_name] = hashlib.sha256(content).hexdigest()
    write_json(
        CLOUDFLARE_RUNTIME_SOURCE_MANIFEST_PATH,
        {
            "schema_version": "cloudflare-runtime-source-manifest-v1",
            "generation": "mechanical_copy_from_scripts",
            "modules": checksums,
        },
    )


def main() -> int:
    bundle = build_bundle()
    write_json(RUNTIME_POLICY_BUNDLE_PATH, bundle)
    write_python_module(bundle)
    write_runtime_sources()
    print(f"Wrote {RUNTIME_POLICY_BUNDLE_PATH}")
    print(f"Wrote {CLOUDFLARE_RUNTIME_BUNDLE_MODULE_PATH}")
    print(f"Wrote runtime sources to {CLOUDFLARE_RUNTIME_SOURCE_DIR}")
    print(f"Bundle checksum: {bundle['bundle_checksum']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
