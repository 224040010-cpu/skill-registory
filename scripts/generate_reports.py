#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_reports.py — Governance Report Generator

Generates three output files from registry data + CI results:

  reports/pr_comment.md    Layer 1 executive + Layer 2 impact  (→ PR comment)
  reports/job_summary.md   Layer 2 engineering full view        (→ Job Summary)
  reports/summary.json     Layer 1 structured data              (→ badges / trends)

Context modes (--context):
  pr     PR-focused: changed assets, blast radius, bundle impact
  merge  Post-merge: full dashboard + allowlist stats
  cron   Weekly audit: full dashboard + governance findings
  manual Full dashboard, no PR-specific data

Usage:
  python scripts/generate_reports.py
  python scripts/generate_reports.py --context pr --changed /tmp/changed_files.txt
  python scripts/generate_reports.py --context merge
  python scripts/generate_reports.py --context cron \\
      --governance-report reports/governance/audit-2026-03-18.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import date
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required — pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REPO_ROOT    = Path(__file__).parent.parent
REPORTS_DIR  = REPO_ROOT / "reports"
RISK_ORDER   = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
ACTIVE_STS   = {"approved", "restricted"}


# ─────────────────────────────────────────────────────────────────
# Data loaders
# ─────────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_changed_files(path: Path) -> list[str]:
    if not path or not path.exists():
        return []
    return [f.strip() for f in path.read_text(encoding="utf-8").splitlines() if f.strip()]


def build_tool_consumers(tools: list, skill_map: dict) -> dict[str, list]:
    """tool_name → [skill_names] (only active consumers)."""
    result: dict[str, list] = {}
    for t in tools:
        consumers = [
            c for c in (t.get("called_by_skills") or [])
            if skill_map.get(c, {}).get("status") in ACTIVE_STS
        ]
        result[t["tool_name"]] = consumers
    return result


# ─────────────────────────────────────────────────────────────────
# Layer 1 — Executive summary
# ─────────────────────────────────────────────────────────────────

def compute_exec_summary(
    skills: list, tools: list,
    ci_summary: dict,
    state_guard: dict,
    changed_files: list[str],
) -> dict:
    """Compute the numbers that go into Layer 1 (badges, exec table)."""

    skill_map = {s["skill_name"]: s for s in skills}
    tool_consumers = build_tool_consumers(tools, skill_map)

    # Platform score (simplified version of bundle_dashboard logic)
    stale_count = 0
    today = date.today()
    for s in skills:
        lr = s.get("last_reviewed", "")
        if lr:
            try:
                d = date.fromisoformat(str(lr))
                if (today - d).days > 180:
                    stale_count += 1
            except ValueError:
                pass

    eval_failing  = sum(1 for s in skills if s.get("eval_status") == "failing")
    ci_blocked    = ci_summary.get("blocked", 0)
    deprecated    = sum(1 for s in skills if s.get("status") == "deprecated")
    total_skills  = len(skills)
    approved      = sum(1 for s in skills if s.get("status") in ACTIVE_STS)
    l3_l4         = sum(1 for s in skills
                        if RISK_ORDER.get(s.get("risk_level", "L1"), 1) >= 3
                        and s.get("status") in ACTIVE_STS)

    score = 100
    score -= min(deprecated / max(total_skills, 1) * 50, 20)
    score -= min(stale_count / max(total_skills, 1) * 40, 25)
    score -= eval_failing * 10
    score -= ci_blocked   * 5
    score += approved / max(total_skills, 1) * 5
    platform_score = max(0, min(100, round(score)))

    # Orphan tools (no active consumers)
    orphan_tools = [
        t["tool_name"] for t in tools
        if t.get("status") in ACTIVE_STS
        and not tool_consumers.get(t["tool_name"])
    ]

    # High-risk chains
    skill_tools: dict[str, list] = defaultdict(list)
    for t in tools:
        for c in (t.get("called_by_skills") or []):
            if c in skill_map:
                skill_tools[c].append(t["tool_name"])

    high_risk_chains = []
    for skill_name, tool_names in skill_tools.items():
        s = skill_map.get(skill_name, {})
        if s.get("status") not in ACTIVE_STS:
            continue
        skill_risk = RISK_ORDER.get(s.get("risk_level", "L1"), 1)
        for tn in tool_names:
            t = next((x for x in tools if x["tool_name"] == tn), {})
            if RISK_ORDER.get(t.get("risk_level", "L1"), 1) > skill_risk:
                high_risk_chains.append(f"{skill_name} → {tn}")

    # Blast radius of this PR
    blast_skills: set  = set()
    blast_bundles: set = set()
    for fpath in changed_files:
        parts = Path(fpath).parts
        if not parts:
            continue
        # For a changed TOOL.md, find all skills that call it
        if Path(fpath).name == "TOOL.md":
            bundle_dir = parts[0]
            for t in tools:
                if t.get("path", "").startswith(bundle_dir):
                    for c in (t.get("called_by_skills") or []):
                        if c in skill_map:
                            blast_skills.add(c)
                            b = skill_map[c].get("bundle_scope", "")
                            if b:
                                blast_bundles.add(b)
        # For a changed SKILL.md, the skill itself + any skills that depend on it
        elif Path(fpath).name == "SKILL.md":
            bundle_dir  = parts[0]
            for s in skills:
                if s.get("path", "").startswith(bundle_dir):
                    blast_skills.add(s["skill_name"])
                    b = s.get("bundle_scope", "")
                    if b:
                        blast_bundles.add(b)
                    for other in skills:
                        if s["skill_name"] in (other.get("dependencies") or []):
                            blast_skills.add(other["skill_name"])

    # Determine overall health flag
    sg_result = state_guard.get("result", "PASS")
    if sg_result == "FAIL" or ci_blocked > 0 or eval_failing > 0:
        health_flag = "HIGH"
    elif stale_count > 5 or len(high_risk_chains) > 0:
        health_flag = "WARNING"
    else:
        health_flag = "OK"

    return {
        "platform_score":    platform_score,
        "total_skills":      total_skills,
        "total_tools":       len(tools),
        "approved_skills":   approved,
        "l3_l4_skills":      l3_l4,
        "orphan_tools":      len(orphan_tools),
        "orphan_tool_names": orphan_tools,
        "high_risk_chains":  len(high_risk_chains),
        "high_risk_list":    high_risk_chains[:5],
        "stale_count":       stale_count,
        "eval_failing":      eval_failing,
        "ci_blocked":        ci_blocked,
        "deprecated":        deprecated,
        "state_guard":       sg_result,
        "blast_radius":      len(blast_skills),
        "blast_skills":      sorted(blast_skills),
        "blast_bundles":     sorted(blast_bundles),
        "health_flag":       health_flag,
        "generated_at":      str(date.today()),
    }


# ─────────────────────────────────────────────────────────────────
# Layer 2 — Engineering view (bundle dashboard table)
# ─────────────────────────────────────────────────────────────────

def bundle_table_markdown(skills: list, tools: list, ci_data: dict) -> str:
    from math import gcd
    skill_map    = {s["skill_name"]: s for s in skills}
    by_bundle: dict[str, list] = defaultdict(list)
    for s in skills:
        by_bundle[s.get("bundle_scope", "_unscoped")].append(s)

    stale_cutoff_days = 180
    today = date.today()

    lines = [
        "| Bundle | Skills | Tools | OK | Depr% | L3/4 | EvalP | Stale | Backlog | Score | Flag |",
        "|--------|--------|-------|----|-------|------|-------|-------|---------|-------|------|",
    ]

    for bundle, bundle_skills in sorted(by_bundle.items()):
        n = len(bundle_skills)
        ok  = sum(1 for s in bundle_skills if s.get("status") in ACTIVE_STS)
        dep = sum(1 for s in bundle_skills if s.get("status") == "deprecated")
        l34 = sum(1 for s in bundle_skills
                  if RISK_ORDER.get(s.get("risk_level", "L1"), 1) >= 3
                  and s.get("status") in ACTIVE_STS)
        ev  = sum(1 for s in bundle_skills
                  if s.get("eval_status") == "pending"
                  and s.get("status") in ACTIVE_STS)
        stale = 0
        for s in bundle_skills:
            lr = s.get("last_reviewed", "")
            if lr:
                try:
                    d = date.fromisoformat(str(lr))
                    if (today - d).days > stale_cutoff_days and s.get("status") in ACTIVE_STS:
                        stale += 1
                except ValueError:
                    pass

        # Tools used by this bundle
        btools = set()
        for t in tools:
            for c in (t.get("called_by_skills") or []):
                if skill_map.get(c, {}).get("bundle_scope") == bundle:
                    btools.add(t["tool_name"])
        nt = len(btools)

        backlog   = stale + sum(1 for s in bundle_skills
                                if s.get("security_review") == "pending"
                                and s.get("status") in ACTIVE_STS)
        dep_ratio = f"{round(dep/n*100)}%" if n else "0%"

        # Score
        score = 100
        if n:
            score -= min(dep/n*50, 20)
            score -= min(stale/n*40, 25)
            score -= sum(1 for s in bundle_skills if s.get("eval_status") == "failing") * 10
            ci_blk = sum(1 for s in bundle_skills
                         if ci_data.get(s["skill_name"], {}).get("overall", "") in
                         ("REQUIRES_REVIEW", "REJECT"))
            score -= ci_blk * 5
            score += ok/n * 5
        score = max(0, min(100, round(score)))

        flag = "✅" if score >= 70 else ("⚠️" if score >= 40 else "🚨")
        lines.append(
            f"| `{bundle}` | {n} | {nt} | {ok} | {dep_ratio} "
            f"| {l34} | {ev} | {stale} | {backlog} | {score} | {flag} |"
        )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Report builders
# ─────────────────────────────────────────────────────────────────

def build_pr_comment(
    exec_summary: dict,
    ci_summary:   dict,
    state_guard:  dict,
    skills: list, tools: list,
) -> str:
    es = exec_summary
    icon_map = {"OK": "✅", "WARNING": "⚠️", "HIGH": "🚨"}
    flag_icon = icon_map.get(es["health_flag"], "❓")

    lines = [f"## {flag_icon} Governance Impact Analysis\n"]

    # ── Layer 1: Executive numbers ──────────────────────────────
    lines += [
        "### Platform Health\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Platform Score | **{es['platform_score']}/100** |",
        f"| Orphan Tools | {es['orphan_tools']} |",
        f"| High-Risk Chains | {es['high_risk_chains']} |",
        f"| Stale Reviews | {es['stale_count']} |",
        f"| State Guard | {es['state_guard']} |",
        "",
    ]

    # ── PR Impact ───────────────────────────────────────────────
    blast = es["blast_radius"]
    bundles_hit = es["blast_bundles"]

    lines += [
        "### This PR's Impact\n",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Changed assets | {ci_summary.get('total', 0)} "
        f"({ci_summary.get('passed', 0)} pass · {ci_summary.get('blocked', 0)} blocked) |",
        f"| Blast radius | {blast} skill(s) across {len(bundles_hit)} bundle(s) |",
        f"| Affected bundles | {', '.join(f'`{b}`' for b in bundles_hit) or '—'} |",
        "",
    ]

    if es["blast_skills"]:
        lines.append(f"<details><summary>Affected skills ({blast})</summary>\n")
        for s in es["blast_skills"]:
            lines.append(f"- `{s}`")
        lines.append("</details>\n")

    # ── Changed assets table ────────────────────────────────────
    results = ci_summary.get("results", [])
    if results:
        lines += [
            "### Changed Asset Results\n",
            "| Asset | Type | Validate | Admission | Overall |",
            "|-------|------|----------|-----------|---------|",
        ]
        for r in results:
            ov   = r.get("overall", "")
            ov_icon = {
                "PASS":              "✅ PASS",
                "PASS_WITH_WARNINGS": "⚠️ PASS_W",
                "REQUIRES_REVIEW":   "❌ REVIEW",
                "REJECT":            "🚫 REJECT",
            }.get(ov, ov)
            lines.append(
                f"| `{r['asset_name']}` | {r['asset_type']} "
                f"| {r['validate'].get('result','?')} "
                f"| {r['admission'].get('decision','?')} "
                f"| {ov_icon} |"
            )

        blocked = [r for r in results if r.get("overall") in ("REJECT", "REQUIRES_REVIEW")]
        if blocked:
            lines.append("\n**Blocking Issues:**\n")
            for r in blocked:
                lines.append(f"**`{r['asset_name']}`** → {r['overall']}")
                for issue in (r["validate"].get("blocking_issues") or [])[:4]:
                    lines.append(f"- {str(issue)[:110]}")
            lines.append("")

    # ── State guard ─────────────────────────────────────────────
    sg_result   = state_guard.get("result", "PASS")
    sg_findings = state_guard.get("findings", [])
    sg_icon     = icon_map.get(sg_result, "")
    lines += [f"### State Guard: {sg_icon} {sg_result}\n"]

    if sg_findings:
        for f in sg_findings[:5]:
            sev_icon = {"CRITICAL": "🚨", "HIGH": "❌", "WARNING": "⚠️"}.get(f["severity"], "")
            lines.append(
                f"- {sev_icon} `[{f['rule']}]` **{f['asset_type']}:{f['asset_name']}** "
                f"— {f['message']}"
            )
        lines.append("")

    # ── Bundle scores ───────────────────────────────────────────
    lines += [
        "<details><summary>Bundle Scores (current state)</summary>\n",
        bundle_table_markdown(skills, tools, {}),
        "</details>\n",
        f"\n---\n*Governance CI · {es['generated_at']} · "
        f"[Full report in Actions Job Summary]("
        f"https://github.com/hazezhang/skill-registry/actions)*",
    ]

    return "\n".join(lines)


def build_job_summary(
    exec_summary: dict,
    ci_summary:   dict,
    skills: list, tools: list,
    governance_report: dict,
    context: str,
) -> str:
    es   = exec_summary
    icon = {"OK": "✅", "WARNING": "⚠️", "HIGH": "🚨"}.get(es["health_flag"], "")

    lines = [f"# {icon} Governance Report — {es['generated_at']}\n"]

    # ── Layer 1: Platform health card ──────────────────────────
    lines += [
        "## Platform Health\n",
        f"| Platform Score | Skills | Tools | Orphan Tools | High-Risk Chains | Stale Reviews |",
        f"|----------------|--------|-------|--------------|-----------------|---------------|",
        f"| **{es['platform_score']}/100** | {es['total_skills']} "
        f"| {es['total_tools']} | {es['orphan_tools']} "
        f"| {es['high_risk_chains']} | {es['stale_count']} |\n",
    ]

    if es["orphan_tool_names"]:
        lines += [
            "**Orphan tools (no active consumers):**",
            " ".join(f"`{t}`" for t in es["orphan_tool_names"]),
            "",
        ]

    if es["high_risk_list"]:
        lines += [
            "**High-risk chains (skill risk < tool risk):**",
        ]
        for chain in es["high_risk_list"]:
            lines.append(f"- {chain}")
        lines.append("")

    # ── Layer 2: Bundle dashboard ──────────────────────────────
    lines += [
        "## Bundle Quality Dashboard\n",
        bundle_table_markdown(skills, tools, {}),
        "",
        "> Scores: ✅ ≥ 70 · ⚠️ 40–69 · 🚨 < 40  "
        "| Columns: OK=approved, EvalP=eval_pending, Backlog=stale+sec_pending\n",
    ]

    # ── CI results for this run ────────────────────────────────
    if ci_summary.get("total", 0) > 0:
        lines += [
            "## This Run — Asset Results\n",
            f"Checked: {ci_summary['total']}  "
            f"Passed: {ci_summary['passed']}  "
            f"Blocked: {ci_summary['blocked']}\n",
        ]
        blocked = [r for r in ci_summary.get("results", [])
                   if r.get("overall") in ("REJECT", "REQUIRES_REVIEW")]
        if blocked:
            lines.append("**Blocked assets:**\n")
            for r in blocked:
                lines.append(f"- `{r['asset_name']}` → {r['overall']}")
        lines.append("")

    # ── Governance findings (if cron context) ─────────────────
    if context == "cron" and governance_report:
        total_f = governance_report.get("total_findings", 0)
        crit_f  = governance_report.get("critical_findings", 0)
        lines += [
            "## Governance Audit Findings\n",
            f"Total: {total_f}  Critical: {crit_f}\n",
        ]
        by_type = governance_report.get("by_asset_type", {})
        if by_type:
            lines += [
                "| Asset Type | Findings |",
                "|------------|---------|",
            ]
            for atype, count in sorted(by_type.items()):
                lines.append(f"| {atype} | {count} |")
            lines.append("")

    # ── Allowlist snapshot ─────────────────────────────────────
    allowlist_path = REPO_ROOT / "runtime" / "allowlist.json"
    if allowlist_path.exists():
        al = load_json(allowlist_path)
        sm = al.get("summary", {})
        lines += [
            "## Published Capability Catalog\n",
            f"| Approved Skills | Approved Tools | Generated |",
            f"|----------------|----------------|-----------|",
            f"| {sm.get('allowed_skills', '?')} "
            f"| {sm.get('allowed_tools', '?')} "
            f"| {al.get('generated_at', '?')[:19]} |\n",
        ]

    lines.append(f"\n*Generated by `scripts/generate_reports.py` · context: {context}*")
    return "\n".join(lines)


def build_summary_json(exec_summary: dict, ci_summary: dict) -> dict:
    """Structured data for shields.io dynamic badges."""
    es = exec_summary
    return {
        "generated_at":    es["generated_at"],
        "platform_score":  es["platform_score"],
        "health_flag":     es["health_flag"],
        "total_skills":    es["total_skills"],
        "total_tools":     es["total_tools"],
        "orphan_tools":    es["orphan_tools"],
        "high_risk_chains": es["high_risk_chains"],
        "stale_reviews":   es["stale_count"],
        "ci_blocked":      es["ci_blocked"],
        "state_guard":     es["state_guard"],
        # Badge-friendly fields
        "badge": {
            "platform_score": {
                "schemaVersion": 1,
                "label": "Platform Score",
                "message": f"{es['platform_score']}/100",
                "color": (
                    "brightgreen" if es["platform_score"] >= 70 else
                    "yellow"      if es["platform_score"] >= 40 else
                    "red"
                ),
            },
            "health": {
                "schemaVersion": 1,
                "label": "Governance",
                "message": es["health_flag"],
                "color": {
                    "OK": "brightgreen", "WARNING": "yellow", "HIGH": "red"
                }.get(es["health_flag"], "lightgray"),
            },
            "orphan_tools": {
                "schemaVersion": 1,
                "label": "Orphan Tools",
                "message": str(es["orphan_tools"]),
                "color": "red" if es["orphan_tools"] > 0 else "brightgreen",
            },
        },
    }


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Governance Report Generator")
    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--changed",        help="File with list of changed paths")
    parser.add_argument("--ci-summary",     default="reports/admission/ci_summary.json",
                        help="Path to ci_summary.json (PR/merge context)")
    parser.add_argument("--state-guard",    default="reports/admission/state-guard.json")
    parser.add_argument("--governance-report", help="Path to governance_audit output JSON")
    parser.add_argument("--context",
                        choices=["pr", "merge", "cron", "manual"],
                        default="manual")
    parser.add_argument("--output-dir",     default="reports")
    args = parser.parse_args()

    # ── Load data ──────────────────────────────────────────────
    skill_data = load_yaml(Path(args.skill_registry))
    tool_data  = load_yaml(Path(args.tool_registry))
    skills     = skill_data.get("skills", [])
    tools      = tool_data.get("tools",   [])

    ci_summary    = load_json(Path(args.ci_summary))
    state_guard   = load_json(Path(args.state_guard))
    gov_report    = {}
    if args.governance_report:
        gov_report = load_json(Path(args.governance_report))

    changed_files = load_changed_files(Path(args.changed) if args.changed else None)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Compute ────────────────────────────────────────────────
    exec_summary = compute_exec_summary(
        skills, tools, ci_summary, state_guard, changed_files)

    # ── Layer 1+2: PR comment ──────────────────────────────────
    pr_md = build_pr_comment(exec_summary, ci_summary, state_guard, skills, tools)
    (out_dir / "pr_comment.md").write_text(pr_md, encoding="utf-8")

    # ── Layer 2: Job summary ───────────────────────────────────
    job_md = build_job_summary(
        exec_summary, ci_summary, skills, tools, gov_report, args.context)
    (out_dir / "job_summary.md").write_text(job_md, encoding="utf-8")

    # ── Layer 1: summary.json (for badges) ────────────────────
    summary_json = build_summary_json(exec_summary, ci_summary)
    (out_dir / "summary.json").write_text(
        json.dumps(summary_json, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Reports written to {out_dir}/")
    print(f"  pr_comment.md  ({len(pr_md)} chars)")
    print(f"  job_summary.md ({len(job_md)} chars)")
    print(f"  summary.json   (score={exec_summary['platform_score']}, "
          f"flag={exec_summary['health_flag']})")


if __name__ == "__main__":
    main()
