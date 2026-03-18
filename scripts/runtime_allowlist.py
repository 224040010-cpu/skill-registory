#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runtime_allowlist.py — Generate Runtime-Consumable Asset Allowlist

Reads skill-registry.yaml and tool-registry.yaml, filters to only
approved / restricted assets, and writes runtime/allowlist.json.

The allowlist is the CONTRACT between the registry and the runtime:
  - ONLY approved / restricted assets appear in the allowlist.
  - draft / submitted / needs_revision / deprecated / retired are excluded.
  - The runtime MUST NOT call any asset not present in this file.

Usage:
    python scripts/runtime_allowlist.py
    python scripts/runtime_allowlist.py --output runtime/allowlist.json

Exit codes:
    0 — Success
    1 — No approved assets found (allowlist empty — likely a config problem)
    2 — Parse error / missing registry
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required — run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

RUNTIME_ELIGIBLE_STATUSES = {"approved", "restricted"}


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def skill_to_runtime_entry(skill: dict) -> dict:
    """Return the runtime-facing skill descriptor (no internal governance fields)."""
    return {
        "name":             skill["skill_name"],
        "display_name":     skill.get("display_name", skill["skill_name"]),
        "version":          skill.get("version", "0.0.0"),
        "status":           skill.get("status"),
        "risk_level":       skill.get("risk_level", "L2"),
        "bundle_scope":     skill.get("bundle_scope", ""),
        "path":             skill.get("path", ""),
        "owner_team":       skill.get("owner_team", ""),
        "supported_models": skill.get("supported_models") or [],
        "dependencies":     skill.get("dependencies") or [],
    }


def tool_to_runtime_entry(tool: dict) -> dict:
    """Return the runtime-facing tool descriptor."""
    service  = tool.get("service", "")
    endpoint = tool.get("endpoint", "")
    if not endpoint and service:
        # Reconstruct canonical endpoint from service + tool name
        safe_name = tool["tool_name"].replace("-", "_")
        endpoint = f"{service}:{safe_name}()"

    return {
        "name":             tool["tool_name"],
        "display_name":     tool.get("display_name", tool["tool_name"]),
        "version":          tool.get("version", "0.0.0"),
        "status":           tool.get("status"),
        "category":         tool.get("category", ""),
        "risk_level":       tool.get("risk_level", "L1"),
        "service":          service,
        "endpoint":         endpoint,
        "idempotent":       tool.get("idempotent", True),
        "requires_approval": tool.get("requires_approval", False),
        "side_effects":     tool.get("side_effects", "none"),
    }


def build_allowlist(skill_data: dict, tool_data: dict) -> dict:
    skills = skill_data.get("skills", [])
    tools  = tool_data.get("tools",  [])

    allowed_skills:  list  = []
    excluded_skills: dict  = {}
    allowed_tools:   list  = []
    excluded_tools:  dict  = {}

    for skill in skills:
        status = skill.get("status", "draft")
        name   = skill.get("skill_name", "<unknown>")
        if status in RUNTIME_ELIGIBLE_STATUSES:
            allowed_skills.append(skill_to_runtime_entry(skill))
        else:
            excluded_skills.setdefault(status, []).append(name)

    for tool in tools:
        status = tool.get("status", "draft")
        name   = tool.get("tool_name", "<unknown>")
        if status in RUNTIME_ELIGIBLE_STATUSES:
            allowed_tools.append(tool_to_runtime_entry(tool))
        else:
            excluded_tools.setdefault(status, []).append(name)

    return {
        "schema_version": "1.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "source": {
            "skill_registry_version":  skill_data.get("schema_version", "unknown"),
            "tool_registry_version":   tool_data.get("schema_version", "unknown"),
            "skill_registry_audited":  skill_data.get("last_audited", ""),
            "tool_registry_audited":   tool_data.get("last_audited", ""),
        },
        "summary": {
            "allowed_skills": len(allowed_skills),
            "allowed_tools":  len(allowed_tools),
            "excluded_skills_by_status": {k: len(v) for k, v in excluded_skills.items()},
            "excluded_tools_by_status":  {k: len(v) for k, v in excluded_tools.items()},
        },
        # Runtime reads these two arrays to build its candidate set
        "skills": allowed_skills,
        "tools":  allowed_tools,
        # Excluded section is informational (e.g. for dashboards)
        "excluded": {
            "skills": excluded_skills,
            "tools":  excluded_tools,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate runtime asset allowlist from registry files")
    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--output",         default="runtime/allowlist.json")
    args = parser.parse_args()

    skill_path = Path(args.skill_registry)
    tool_path  = Path(args.tool_registry)

    for p in (skill_path, tool_path):
        if not p.exists():
            print(f"ERROR: Registry not found: {p}", file=sys.stderr)
            sys.exit(2)

    skill_data = load_yaml(skill_path)
    tool_data  = load_yaml(tool_path)

    allowlist = build_allowlist(skill_data, tool_data)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(allowlist, f, indent=2, ensure_ascii=False)

    s = allowlist["summary"]
    excluded_s = sum(s["excluded_skills_by_status"].values())
    excluded_t = sum(s["excluded_tools_by_status"].values())

    print(f"Runtime allowlist → {out}")
    print(f"  Skills: {s['allowed_skills']} allowed  "
          f"/ {excluded_s} excluded ({dict(s['excluded_skills_by_status'])})")
    print(f"  Tools:  {s['allowed_tools']} allowed  "
          f"/ {excluded_t} excluded ({dict(s['excluded_tools_by_status'])})")

    if s["allowed_skills"] == 0 and s["allowed_tools"] == 0:
        print("\nWARNING: Allowlist is empty — no approved assets found!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
