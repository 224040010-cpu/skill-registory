#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_fix_frontmatter.py — Batch-patch SKILL.md frontmatter from skill-registry.yaml.

Adds missing fields (bundle_scope, risk_level) using the registry as the source
of truth. Skips files that already have both fields. Does NOT overwrite existing
values unless --overwrite is passed.

Usage:
    python scripts/batch_fix_frontmatter.py [--dry-run] [--overwrite]
    python scripts/batch_fix_frontmatter.py --bundles ev-charger-skills business-to-bpmn
"""

import sys
import re
import yaml
import io
from pathlib import Path

# Force UTF-8 stdout on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REGISTRY_PATH = Path("skill-registry.yaml")
DRY_RUN   = "--dry-run"  in sys.argv
OVERWRITE = "--overwrite" in sys.argv

# Parse --bundles flag
if "--bundles" in sys.argv:
    idx = sys.argv.index("--bundles")
    BUNDLE_FILTER = set(sys.argv[idx + 1:])
else:
    BUNDLE_FILTER = set()


# ─────────────────────────────────────────────
# Registry loader
# ─────────────────────────────────────────────

def load_registry() -> dict[str, dict]:
    """Return dict keyed by skill_name → registry entry."""
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {s["skill_name"]: s for s in data.get("skills", [])}


# ─────────────────────────────────────────────
# Frontmatter parser / writer
# ─────────────────────────────────────────────

def parse_frontmatter_raw(content: str) -> tuple[str, str, str]:
    """Return (before_fm, fm_block, body).
    before_fm is always '' since SKILL.md starts with ---.
    """
    if not content.startswith("---"):
        return "", "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", parts[1] if len(parts) > 1 else "", ""
    return "", parts[1], parts[2]


def read_frontmatter_fields(fm_block: str) -> dict[str, str]:
    """Quick key:value reader for simple frontmatter fields."""
    fields = {}
    current_key = None
    current_lines = []
    for line in fm_block.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            if current_key:
                fields[current_key] = " ".join(current_lines).strip()
            key, _, val = line.partition(":")
            current_key = key.strip()
            current_lines = [val.strip()] if val.strip() else []
        elif current_key:
            current_lines.append(line.strip())
    if current_key:
        fields[current_key] = " ".join(current_lines).strip()
    return fields


def inject_fields(fm_block: str, fields_to_add: dict[str, str]) -> str:
    """
    Append missing fields to the end of the frontmatter block.
    Each added field appears on its own line.
    Returns the updated frontmatter block.
    """
    lines = fm_block.rstrip().splitlines()
    for key, value in fields_to_add.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def patch_skill_md(path: Path, add_fields: dict[str, str]) -> bool:
    """
    Patch a SKILL.md file with the given fields.
    Returns True if file was modified (or would be in dry-run).
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"  [SKIP] Cannot read {path}: {e}")
        return False

    _, fm_block, body = parse_frontmatter_raw(content)
    if not fm_block and not body:
        print(f"  [SKIP] No frontmatter in {path}")
        return False

    existing = read_frontmatter_fields(fm_block)

    to_inject = {}
    for key, value in add_fields.items():
        if key not in existing:
            to_inject[key] = value
        elif OVERWRITE and existing[key] != value:
            # Replace existing value
            to_inject[key] = None  # mark for replacement

    if not to_inject and not OVERWRITE:
        return False  # nothing to do

    # Handle overwrites: remove old lines first, then append
    if OVERWRITE:
        new_lines = []
        for line in fm_block.splitlines():
            line_key = line.split(":")[0].strip() if ":" in line else ""
            if line_key in add_fields and not line.startswith(" "):
                continue  # remove old value
            new_lines.append(line)
        fm_block = "\n".join(new_lines) + "\n"
        to_inject = add_fields

    if not to_inject:
        return False

    new_fm = inject_fields(fm_block, to_inject)
    new_content = f"---{new_fm}---{body}"

    if DRY_RUN:
        print(f"  [DRY-RUN] Would add to {path}:")
        for k, v in to_inject.items():
            print(f"            {k}: {v}")
        return True

    path.write_text(new_content, encoding="utf-8")
    return True


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    registry = load_registry()
    print(f"Loaded {len(registry)} registry entries.")
    print(f"Mode: {'DRY-RUN' if DRY_RUN else 'WRITE'}  |  Overwrite: {OVERWRITE}\n")

    stats = {"patched": 0, "skipped": 0, "not_in_registry": 0, "error": 0}
    not_in_registry = []

    # Discover all SKILL.md files
    root = Path(".")
    all_skills = [p for p in root.rglob("SKILL.md")
                  if not any(part.startswith(".") for part in p.parts)]

    # Filter by bundle if requested
    if BUNDLE_FILTER:
        all_skills = [p for p in all_skills
                      if any(b in str(p) for b in BUNDLE_FILTER)]

    print(f"Found {len(all_skills)} SKILL.md file(s) to process.\n")

    for path in sorted(all_skills):
        dir_name = path.parent.name
        reg = registry.get(dir_name)

        if reg is None:
            stats["not_in_registry"] += 1
            not_in_registry.append(str(path))
            continue

        fields_to_add = {}
        if "bundle_scope" in reg and reg["bundle_scope"]:
            fields_to_add["bundle_scope"] = reg["bundle_scope"]
        if "risk_level" in reg and reg["risk_level"]:
            fields_to_add["risk_level"] = reg["risk_level"]

        if not fields_to_add:
            stats["skipped"] += 1
            continue

        modified = patch_skill_md(path, fields_to_add)
        if modified:
            added = list(fields_to_add.keys())
            print(f"  [PATCHED] {path}  +{added}")
            stats["patched"] += 1
        else:
            stats["skipped"] += 1

    print(f"\n{'=' * 60}")
    print(f"  Patched : {stats['patched']}")
    print(f"  Skipped : {stats['skipped']}  (already have fields)")
    print(f"  Unknown : {stats['not_in_registry']}  (not in registry)")
    if not_in_registry:
        print(f"\n  Skills not in registry (need manual registration):")
        for p in not_in_registry:
            print(f"    {p}")
    print()

    if not DRY_RUN and stats["patched"] > 0:
        print("  Next step: re-run batch_admission.py to verify fixes:")
        print("    python scripts/batch_admission.py ev-charger-skills business-to-bpmn\n")


if __name__ == "__main__":
    main()
