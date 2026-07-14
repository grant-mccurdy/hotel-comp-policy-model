from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "policy.v1.json"
POLICY_SCENARIOS_PATH = PROJECT_ROOT / "config" / "policy_scenarios.v1.json"


class PolicyConfigError(ValueError):
    pass


@lru_cache(maxsize=4)
def load_policy_config(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    policy_path = Path(path)
    if not policy_path.exists():
        raise PolicyConfigError(f"Policy configuration not found: {policy_path}")
    with policy_path.open("r", encoding="utf-8") as handle:
        policy = json.load(handle)
    required = {
        "policy_id",
        "policy_version",
        "policy_status",
        "recovery_need_weights",
        "tier_thresholds",
        "manager_review",
        "failure_base_risk",
        "comp_fit",
        "comp_catalog",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise PolicyConfigError(f"Policy configuration missing keys: {', '.join(missing)}")
    if len(policy["tier_thresholds"]) != 4:
        raise PolicyConfigError("Policy tier_thresholds must contain four ascending values")
    if list(policy["tier_thresholds"]) != sorted(policy["tier_thresholds"]):
        raise PolicyConfigError("Policy tier_thresholds must be ascending")
    codes = [row.get("comp_code") for row in policy["comp_catalog"]]
    if len(codes) != len(set(codes)):
        raise PolicyConfigError("Policy comp_catalog contains duplicate comp_code values")
    return policy


@lru_cache(maxsize=1)
def load_policy_scenarios(path: str | Path = POLICY_SCENARIOS_PATH) -> dict[str, Any]:
    scenario_path = Path(path)
    if not scenario_path.exists():
        raise PolicyConfigError(f"Policy scenario configuration not found: {scenario_path}")
    with scenario_path.open("r", encoding="utf-8") as handle:
        scenarios = json.load(handle)
    required = {
        "comparison_version",
        "reference_policy_id",
        "bootstrap",
        "probabilistic_sensitivity",
        "evaluation",
        "shadow_guardrails",
        "policies",
    }
    missing = sorted(required - set(scenarios))
    if missing:
        raise PolicyConfigError(f"Policy scenario configuration missing keys: {', '.join(missing)}")
    policy_ids = [row.get("policy_id") for row in scenarios["policies"]]
    if len(policy_ids) != len(set(policy_ids)):
        raise PolicyConfigError("Policy scenarios contain duplicate policy_id values")
    if scenarios["reference_policy_id"] not in policy_ids:
        raise PolicyConfigError("reference_policy_id must identify a configured policy")
    return scenarios


def comp_catalog(policy: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    selected = policy or load_policy_config()
    return [{**row, "policy_version": selected["policy_version"]} for row in selected["comp_catalog"]]
