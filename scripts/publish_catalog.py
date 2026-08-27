#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_catalog.py — Publish a versioned, runtime-consumable capability catalog

Reads skill-registry.yaml and tool-registry.yaml, filters to only
approved / restricted assets, and writes catalog/catalog.snapshot.json.

The catalog snapshot is the CONTRACT between the registry and workflow compilers:
  - ONLY approved / restricted assets appear in the callable section.
  - draft / submitted / needs_revision / deprecated / retired are excluded.
  - The runtime MUST NOT call any asset not present in this file.

Usage:
    python scripts/publish_catalog.py
    python scripts/publish_catalog.py --output catalog/catalog.snapshot.json

Exit codes:
    0 — Success
    1 — No approved assets found (catalog empty — likely a config problem)
    2 — Parse error / missing registry
"""

import sys
import json
import argparse
import hashlib
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


def asset_digest(asset: dict, registry_root: Path) -> tuple[str, bool]:
    """Digest governance metadata plus source bytes when the source file exists."""
    digest = hashlib.sha256()
    digest.update(json.dumps(asset, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    source = registry_root / asset.get("path", "")
    source_present = source.is_file()
    if source_present:
        digest.update(source.read_bytes())
    return f"sha256:{digest.hexdigest()}", source_present


def skill_to_runtime_entry(skill: dict, registry_root: Path) -> dict:
    """Return the runtime-facing skill descriptor (no internal governance fields)."""
    digest, source_present = asset_digest(skill, registry_root)
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
        "digest":           digest,
        "source_present":   source_present,
    }


def tool_to_runtime_entry(tool: dict, registry_root: Path) -> dict:
    """Return the runtime-facing tool descriptor."""
    service  = tool.get("service", "")
    endpoint = tool.get("endpoint", "")
    if not endpoint and service:
        # Reconstruct canonical endpoint from service + tool name
        safe_name = tool["tool_name"].replace("-", "_")
        endpoint = f"{service}:{safe_name}()"

    digest, source_present = asset_digest(tool, registry_root)
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
        "digest":           digest,
        "source_present":   source_present,
    }


def build_catalog(
    skill_data: dict,
    tool_data: dict,
    system_definition: dict,
    system_definition_digest: str,
    registry_root: Path,
) -> dict:
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
            allowed_skills.append(skill_to_runtime_entry(skill, registry_root))
        else:
            excluded_skills.setdefault(status, []).append(name)

    for tool in tools:
        status = tool.get("status", "draft")
        name   = tool.get("tool_name", "<unknown>")
        if status in RUNTIME_ELIGIBLE_STATUSES:
            allowed_tools.append(tool_to_runtime_entry(tool, registry_root))
        else:
            excluded_tools.setdefault(status, []).append(name)

    return {
        "schema_version": "2.0.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "source": {
            "skill_registry_version":  skill_data.get("schema_version", "unknown"),
            "tool_registry_version":   tool_data.get("schema_version", "unknown"),
            "skill_registry_audited":  skill_data.get("last_audited", ""),
            "tool_registry_audited":   tool_data.get("last_audited", ""),
            "system_definition_version": system_definition.get("definition_version", "unknown"),
            "system_definition_digest": f"sha256:{system_definition_digest}",
        },
        "summary": {
            "allowed_skills": len(allowed_skills),
            "allowed_tools":  len(allowed_tools),
            "excluded_skills_by_status": {k: len(v) for k, v in excluded_skills.items()},
            "excluded_tools_by_status":  {k: len(v) for k, v in excluded_tools.items()},
        },
        # Workflow compilers resolve and pin these descriptors before deployment.
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
        description="Publish a governed capability catalog from registry files")
    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--system-definition", default="contracts/system-definition.json")
    parser.add_argument("--output",         default="catalog/catalog.snapshot.json")
    args = parser.parse_args()

    skill_path = Path(args.skill_registry)
    tool_path  = Path(args.tool_registry)

    definition_path = Path(args.system_definition)

    for p in (skill_path, tool_path, definition_path):
        if not p.exists():
            print(f"ERROR: Registry not found: {p}", file=sys.stderr)
            sys.exit(2)

    skill_data = load_yaml(skill_path)
    tool_data  = load_yaml(tool_path)
    try:
        system_definition = json.loads(definition_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Invalid system definition: {exc}", file=sys.stderr)
        sys.exit(2)
    system_definition_digest = hashlib.sha256(definition_path.read_bytes()).hexdigest()

    catalog = build_catalog(
        skill_data,
        tool_data,
        system_definition,
        system_definition_digest,
        Path.cwd(),
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    s = catalog["summary"]
    excluded_s = sum(s["excluded_skills_by_status"].values())
    excluded_t = sum(s["excluded_tools_by_status"].values())

    print(f"Capability catalog → {out}")
    print(f"  Skills: {s['allowed_skills']} allowed  "
          f"/ {excluded_s} excluded ({dict(s['excluded_skills_by_status'])})")
    print(f"  Tools:  {s['allowed_tools']} allowed  "
          f"/ {excluded_t} excluded ({dict(s['excluded_tools_by_status'])})")

    if s["allowed_skills"] == 0 and s["allowed_tools"] == 0:
        print("\nWARNING: Catalog is empty — no approved assets found!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
