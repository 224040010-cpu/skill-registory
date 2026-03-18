#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bundle_dashboard.py — Bundle-Level Quality Dashboard

Computes per-bundle quality metrics from skill-registry.yaml and
tool-registry.yaml, and cross-references with any available CI reports.

Metrics per bundle:
    skills_total        Total skills in bundle
    tools_used          Unique tools consumed by bundle skills
    skill_tool_ratio    skills : tools ratio
    approved            Approved + restricted skills
    draft               Draft + submitted + needs_revision skills
    deprecated          Deprecated skills
    retired             Retired skills
    deprecated_ratio    deprecated / total skills (%)
    l3_l4_skills        High-risk skills (L3 or L4)
    l3_l4_tools         High-risk tools used by this bundle
    eval_pending        Skills with eval_status: pending
    eval_failing        Skills with eval_status: failing
    security_pending    Active skills with security_review: pending
    stale_reviews       Skills not reviewed in >180 days
    review_backlog      stale_reviews + security_pending (total needs attention)
    ci_pass             Skills with PASS in latest CI report (if available)
    ci_warnings         Skills with PASS_WITH_WARNINGS in latest CI report
    ci_blocked          Skills with REQUIRES_REVIEW or REJECT in CI

Usage:
    python scripts/bundle_dashboard.py
    python scripts/bundle_dashboard.py --json
    python scripts/bundle_dashboard.py --output reports/dashboard.json
    python scripts/bundle_dashboard.py --markdown

Exit codes:
    0 — All bundles healthy
    1 — One or more bundles have HIGH-severity issues
    2 — Parse error
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required — pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ACTIVE_STATUSES   = {"approved", "restricted"}
INACTIVE_STATUSES = {"deprecated", "retired"}
PENDING_STATUSES  = {"draft", "submitted", "needs_revision"}
STALE_DAYS        = 180
RISK_ORDER        = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}

REPO_ROOT = Path(__file__).parent.parent


# ─────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_ci_reports(ci_dir: Path) -> dict[str, dict]:
    """Load per-asset CI reports from reports/ci/ if available."""
    results: dict[str, dict] = {}
    if not ci_dir.exists():
        return results
    for f in ci_dir.glob("ci_*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            name = data.get("asset_name")
            if name:
                results[name] = data
        except Exception:
            pass
    return results


def parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────
# Metrics computation
# ─────────────────────────────────────────────

def compute_bundle_metrics(
    skills:    list,
    tools:     list,
    ci_data:   dict[str, dict],
) -> dict[str, dict]:
    """Return a dict of bundle_name → metrics dict."""

    # Build tool map: tool_name → tool record
    tool_map = {t["tool_name"]: t for t in tools}

    # Build tool → bundles mapping from called_by_skills
    tool_bundles: dict[str, set] = defaultdict(set)
    skill_map = {s["skill_name"]: s for s in skills}
    for t in tools:
        for consumer in (t.get("called_by_skills") or []):
            skill = skill_map.get(consumer)
            if skill:
                b = skill.get("bundle_scope", "_unscoped")
                tool_bundles[t["tool_name"]].add(b)

    # Group skills by bundle
    by_bundle: dict[str, list] = defaultdict(list)
    for s in skills:
        by_bundle[s.get("bundle_scope", "_unscoped")].append(s)

    stale_cutoff = date.today() - timedelta(days=STALE_DAYS)

    dashboards: dict[str, dict] = {}

    for bundle, bundle_skills in sorted(by_bundle.items()):
        m: dict = {}

        # ── Counts by status ────────────────────────────────────────
        m["skills_total"]  = len(bundle_skills)
        m["approved"]      = sum(1 for s in bundle_skills
                                 if s.get("status") in ACTIVE_STATUSES)
        m["draft"]         = sum(1 for s in bundle_skills
                                 if s.get("status") in PENDING_STATUSES)
        m["deprecated"]    = sum(1 for s in bundle_skills
                                 if s.get("status") == "deprecated")
        m["retired"]       = sum(1 for s in bundle_skills
                                 if s.get("status") == "retired")

        depr_ratio = round(m["deprecated"] / m["skills_total"] * 100) \
                     if m["skills_total"] else 0
        m["deprecated_ratio"] = f"{depr_ratio}%"

        # ── Tools used by this bundle ────────────────────────────────
        bundle_tool_names: set[str] = set()
        for t in tools:
            consumers = t.get("called_by_skills") or []
            for c in consumers:
                if skill_map.get(c, {}).get("bundle_scope") == bundle:
                    bundle_tool_names.add(t["tool_name"])
        m["tools_used"] = len(bundle_tool_names)

        # skill : tool ratio
        t_count = m["tools_used"] or 1
        s_count = m["skills_total"] or 1
        from math import gcd
        g = gcd(s_count, t_count)
        m["skill_tool_ratio"] = f"{s_count // g}:{t_count // g}"

        # ── Risk levels ──────────────────────────────────────────────
        m["l3_l4_skills"] = sum(
            1 for s in bundle_skills
            if RISK_ORDER.get(s.get("risk_level", "L1"), 1) >= 3
            and s.get("status") in ACTIVE_STATUSES
        )
        m["l3_l4_tools"] = sum(
            1 for tn in bundle_tool_names
            if RISK_ORDER.get(tool_map.get(tn, {}).get("risk_level", "L1"), 1) >= 3
        )

        # ── Eval & security ──────────────────────────────────────────
        m["eval_pending"] = sum(
            1 for s in bundle_skills
            if s.get("eval_status") == "pending"
            and s.get("status") in ACTIVE_STATUSES
        )
        m["eval_failing"] = sum(
            1 for s in bundle_skills
            if s.get("eval_status") == "failing"
        )
        m["security_pending"] = sum(
            1 for s in bundle_skills
            if s.get("security_review") == "pending"
            and s.get("status") in ACTIVE_STATUSES
        )

        # ── Staleness ────────────────────────────────────────────────
        m["stale_reviews"] = sum(
            1 for s in bundle_skills
            if s.get("status") in ACTIVE_STATUSES
            and (parse_date(s.get("last_reviewed")) or date(2020, 1, 1)) < stale_cutoff
        )
        m["review_backlog"] = m["stale_reviews"] + m["security_pending"]

        # ── CI report cross-reference ────────────────────────────────
        ci_pass    = 0
        ci_warn    = 0
        ci_blocked = 0
        for s in bundle_skills:
            name   = s["skill_name"]
            report = ci_data.get(name, {})
            ov     = report.get("overall", "")
            if ov == "PASS":
                ci_pass += 1
            elif ov == "PASS_WITH_WARNINGS":
                ci_warn += 1
            elif ov in ("REQUIRES_REVIEW", "REJECT"):
                ci_blocked += 1
        m["ci_pass"]     = ci_pass
        m["ci_warnings"] = ci_warn
        m["ci_blocked"]  = ci_blocked
        m["ci_coverage"] = (
            f"{ci_pass + ci_warn + ci_blocked}/{m['skills_total']}"
        )

        # ── Health score (0–100) ─────────────────────────────────────
        # Penalise: deprecated%, stale%, high-risk, eval-pending, blocked CI
        score = 100
        score -= depr_ratio * 0.5                                    # -0.5 per % deprecated
        score -= min(m["stale_reviews"] / max(m["skills_total"], 1) * 40, 30)
        score -= m["eval_failing"] * 10
        score -= m["ci_blocked"] * 15
        score -= m["security_pending"] * 5
        score += m["approved"] / max(m["skills_total"], 1) * 10      # +10 if fully approved
        m["health_score"] = max(0, min(100, round(score)))

        # ── Severity flag ─────────────────────────────────────────────
        if m["ci_blocked"] > 0 or m["eval_failing"] > 0:
            m["health_flag"] = "HIGH"
        elif m["review_backlog"] > 3 or m["deprecated_ratio"] >= "30%":
            m["health_flag"] = "WARNING"
        else:
            m["health_flag"] = "OK"

        dashboards[bundle] = m

    return dashboards


# ─────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────

def print_ascii_table(dashboards: dict):
    # Column definitions: (header, key or lambda, width, align)
    columns = [
        ("Bundle",          "bundle",             22, "<"),
        ("Skills",          "skills_total",         6, ">"),
        ("Tools",           "tools_used",           5, ">"),
        ("S:T",             "skill_tool_ratio",     5, ">"),
        ("OK",              "approved",             4, ">"),
        ("Draft",           "draft",                5, ">"),
        ("Depr%",           "deprecated_ratio",     6, ">"),
        ("L3/4",            "l3_l4_skills",         4, ">"),
        ("EvalP",           "eval_pending",         5, ">"),
        ("Stale",           "stale_reviews",        5, ">"),
        ("Backlog",         "review_backlog",       7, ">"),
        ("CI-OK",           "ci_pass",              5, ">"),
        ("CI-W",            "ci_warnings",          5, ">"),
        ("CI-X",            "ci_blocked",           5, ">"),
        ("Score",           "health_score",         5, ">"),
        ("Flag",            "health_flag",          7, "<"),
    ]

    header  = " | ".join(f"{h:{a}{w}}" for h, _, w, a in columns)
    divider = "-+-".join("-" * w for _, _, w, _ in columns)

    print()
    print("  Bundle Quality Dashboard")
    print()
    print("  " + header)
    print("  " + divider)

    for bundle, m in sorted(dashboards.items()):
        row_data = {"bundle": bundle, **m}
        cells = []
        for h, key, w, a in columns:
            val = str(row_data.get(key, ""))
            cells.append(f"{val:{a}{w}}")
        flag = m.get("health_flag", "")
        icon = {"OK": "[OK]", "WARNING": "[WN]", "HIGH": "[!!]"}.get(flag, "")
        cells[-1] = f"{icon:<7}"
        print("  " + " | ".join(cells))

    print()


def to_markdown(dashboards: dict) -> str:
    lines = ["## Bundle Quality Dashboard\n"]
    lines.append(
        "| Bundle | Skills | Tools | S:T | Approved | Depr% | "
        "L3/4↑ | EvalPend | Stale | Backlog | CI OK | CI Warn | CI Blocked | Score | Flag |"
    )
    lines.append(
        "|--------|--------|-------|-----|----------|-------|"
        "-------|----------|-------|---------|-------|---------|------------|-------|------|"
    )
    for bundle, m in sorted(dashboards.items()):
        flag_icon = {"OK": "✅", "WARNING": "⚠️", "HIGH": "🚨"}.get(m.get("health_flag", ""), "")
        lines.append(
            f"| `{bundle}` "
            f"| {m['skills_total']} "
            f"| {m['tools_used']} "
            f"| {m['skill_tool_ratio']} "
            f"| {m['approved']} "
            f"| {m['deprecated_ratio']} "
            f"| {m['l3_l4_skills']} "
            f"| {m['eval_pending']} "
            f"| {m['stale_reviews']} "
            f"| {m['review_backlog']} "
            f"| {m['ci_pass']} "
            f"| {m['ci_warnings']} "
            f"| {m['ci_blocked']} "
            f"| {m['health_score']} "
            f"| {flag_icon} {m.get('health_flag','')} |"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bundle-Level Quality Dashboard")
    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--ci-reports",     default="reports/ci",
                        help="Directory containing ci_*.json files")
    parser.add_argument("--output",  help="Write JSON dashboard to this path")
    parser.add_argument("--json",    action="store_true", help="Print JSON to stdout")
    parser.add_argument("--markdown", action="store_true", help="Print Markdown table")
    args = parser.parse_args()

    for p in (Path(args.skill_registry), Path(args.tool_registry)):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(2)

    skill_data = load_yaml(Path(args.skill_registry))
    tool_data  = load_yaml(Path(args.tool_registry))
    ci_data    = load_ci_reports(Path(args.ci_reports))

    skills = skill_data.get("skills", [])
    tools  = tool_data.get("tools",   [])

    dashboards = compute_bundle_metrics(skills, tools, ci_data)

    # ── Platform-wide summary ─────────────────────────────────────
    total_skills    = sum(m["skills_total"] for m in dashboards.values())
    total_tools     = len(tools)
    total_backlog   = sum(m["review_backlog"] for m in dashboards.values())
    total_ci_blocked = sum(m["ci_blocked"]    for m in dashboards.values())
    avg_score       = round(
        sum(m["health_score"] for m in dashboards.values()) / max(len(dashboards), 1)
    )

    summary = {
        "generated_at":    str(date.today()),
        "bundles":         len(dashboards),
        "total_skills":    total_skills,
        "total_tools":     total_tools,
        "total_backlog":   total_backlog,
        "total_ci_blocked": total_ci_blocked,
        "platform_health_score": avg_score,
        "bundles_at_risk": [b for b, m in dashboards.items() if m["health_flag"] == "HIGH"],
        "bundles_warning": [b for b, m in dashboards.items() if m["health_flag"] == "WARNING"],
    }

    output_data = {"summary": summary, "bundles": dashboards}

    # ── Outputs ───────────────────────────────────────────────────
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Dashboard written to {args.output}")

    if args.json:
        print(json.dumps(output_data, indent=2, ensure_ascii=False))
        sys.exit(0)

    if args.markdown:
        print(to_markdown(dashboards))
        sys.exit(0)

    # ── Default: ASCII table ───────────────────────────────────────
    print_ascii_table(dashboards)

    print(f"  Platform Summary")
    print(f"  {'-' * 53}")
    print(f"  Bundles:          {summary['bundles']}")
    print(f"  Total Skills:     {summary['total_skills']}")
    print(f"  Total Tools:      {summary['total_tools']}")
    print(f"  Review Backlog:   {summary['total_backlog']}")
    print(f"  CI Blocked:       {summary['total_ci_blocked']}")
    print(f"  Platform Score:   {summary['platform_health_score']}/100")
    if summary["bundles_at_risk"]:
        print(f"  [!!] HIGH:        {summary['bundles_at_risk']}")
    if summary["bundles_warning"]:
        print(f"  [WN] WARNING:     {summary['bundles_warning']}")
    print()

    has_issues = bool(summary["bundles_at_risk"])
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
