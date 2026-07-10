from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "policy.v1.json"


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


def comp_catalog(policy: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    selected = policy or load_policy_config()
    return [{**row, "policy_version": selected["policy_version"]} for row in selected["comp_catalog"]]
