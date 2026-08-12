#!/usr/bin/env python3
"""Construct the deployment workflow's complete bounded public summary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


EXPECTED_ACCOUNT = "241077340022"
EXPECTED_REGION = "us-east-1"
CATEGORIES = {
    "none",
    "validation-failed",
    "identity-failed",
    "foundation-failed",
    "initialization-failed",
    "plan-failed",
    "apply-uncertain",
    "publication-failed",
    "verification-failed",
    "status-failed",
    "renderer-failure",
}
STATUSES = {"success", "safe-failure", "inspection-required"}
ZERO_COUNTS = {"create": 0, "update": 0, "delete": 0, "replace": 0, "read": 0, "no-op": 0}


def action_counts(plan: dict[str, Any] | None) -> dict[str, int]:
    counts = dict(ZERO_COUNTS)
    if plan is None:
        return counts
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("resource_changes must be a list")
    for resource in changes:
        if not isinstance(resource, dict):
            raise ValueError("resource change must be an object")
        actions = resource.get("change", {}).get("actions")
        if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
            raise ValueError("resource actions must be a string list")
        action_set = set(actions)
        if action_set == {"create", "delete"}:
            counts["replace"] += 1
        elif actions == ["create"]:
            counts["create"] += 1
        elif actions == ["update"]:
            counts["update"] += 1
        elif actions == ["delete"]:
            counts["delete"] += 1
        elif actions == ["read"]:
            counts["read"] += 1
        elif actions == ["no-op"]:
            counts["no-op"] += 1
        else:
            raise ValueError("unsupported resource action shape")
    return counts


def fixed_renderer_failure() -> dict[str, Any]:
    return {
        "source_sha": "0" * 40,
        "account": EXPECTED_ACCOUNT,
        "region": EXPECTED_REGION,
        "action_counts": dict(ZERO_COUNTS),
        "category": "renderer-failure",
        "status": "safe-failure",
    }


def build_summary(
    source_sha: str,
    category: str,
    status: str,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
            raise ValueError("invalid source identity")
        if category not in CATEGORIES or status not in STATUSES:
            raise ValueError("unrecognized bounded result")
        return {
            "source_sha": source_sha,
            "account": EXPECTED_ACCOUNT,
            "region": EXPECTED_REGION,
            "action_counts": action_counts(plan),
            "category": category,
            "status": status,
        }
    except (AttributeError, TypeError, ValueError):
        return fixed_renderer_failure()


def append_summary(
    destination: Path,
    source_sha: str,
    category: str,
    status: str,
    plan: dict[str, Any] | None = None,
) -> None:
    document = build_summary(source_sha, category, status, plan)
    encoded = json.dumps(document, separators=(",", ":"), sort_keys=False)
    with destination.open("a", encoding="utf-8") as stream:
        stream.write("## AWS workflow result\n\n")
        stream.write(f"`{encoded}`\n")
