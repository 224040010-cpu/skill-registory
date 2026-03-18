#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_graph.py — Platform Asset Dependency Graph

Builds an explicit graph of all relationships between skills, tools, services,
and bundles from the two registry files.  Supports four query modes plus DOT
export for visual rendering.

Node types:
    skill    — a registered skill (SKILL.md)
    tool     — a registered tool  (TOOL.md)
    service  — an MCP server (grouped tool host)
    bundle   — a bundle scope (e.g. diagnosis-agent)

Edge types:
    calls       skill  → tool    (skill calls this tool)
    depends_on  skill  → skill   (inter-skill dependency)
    belongs_to  tool   → service (tool lives on this server)
    in_bundle   skill  → bundle  (skill is scoped to this bundle)

Queries:
    orphan-tools          Tools with no active consuming skills
    blast-radius          Skills that would break if an asset changes
    high-risk-chains      Skills whose tools have higher risk than the skill itself
    bundle-contamination  Cross-bundle tool sharing (tools used by 2+ bundles)
    summary               Full graph stats (default)

Usage:
    python scripts/asset_graph.py
    python scripts/asset_graph.py --query orphan-tools
    python scripts/asset_graph.py --query blast-radius --asset tool:parse-business-intent
    python scripts/asset_graph.py --query high-risk-chains
    python scripts/asset_graph.py --query bundle-contamination
    python scripts/asset_graph.py --output reports/asset-graph.json
    python scripts/asset_graph.py --dot    reports/asset-graph.dot

Exit codes:
    0 — Success
    1 — Query returned findings that may need attention
    2 — Parse error
"""

import sys
import re
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

REPO_ROOT = Path(__file__).parent.parent

RISK_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
ACTIVE_STATUSES = {"approved", "restricted"}


# ─────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def scan_skill_tool_calls(skill_path: Path) -> list[str]:
    """Scan a SKILL.md body for tool call patterns like service:tool_name()."""
    if not skill_path.exists():
        return []
    text = skill_path.read_text(encoding="utf-8", errors="replace")
    # Match patterns: word:word() or word:word_with_underscores()
    return re.findall(r'[a-z][a-z0-9-]+:[a-z][a-z0-9_]+\(\)', text)


# ─────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────

def build_graph(skill_data: dict, tool_data: dict) -> dict:
    """
    Returns:
      {
        "nodes": { node_id: {type, attrs} },
        "edges": [ {src, dst, rel} ],
        "index": {
          "skills_by_bundle": { bundle: [skill_name] },
          "tools_by_service": { service: [tool_name] },
          "tool_consumers":   { tool_name: [skill_name] },
          "skill_tools":      { skill_name: [tool_name] },
        }
      }
    """
    nodes = {}
    edges = []

    skills = skill_data.get("skills", [])
    tools  = tool_data.get("tools",   [])

    skill_map = {s["skill_name"]: s for s in skills}
    tool_map  = {t["tool_name"]:  t for t in tools}

    # ── Skill nodes ───────────────────────────────────────────────
    for s in skills:
        nid = f"skill:{s['skill_name']}"
        nodes[nid] = {
            "type":    "skill",
            "id":      nid,
            "name":    s["skill_name"],
            "display": s.get("display_name", s["skill_name"]),
            "bundle":  s.get("bundle_scope", ""),
            "risk":    s.get("risk_level", "L1"),
            "status":  s.get("status", "draft"),
            "owner":   s.get("owner_team", ""),
            "eval":    s.get("eval_status", "pending"),
            "path":    s.get("path", ""),
        }

    # ── Tool nodes ────────────────────────────────────────────────
    for t in tools:
        nid = f"tool:{t['tool_name']}"
        nodes[nid] = {
            "type":     "tool",
            "id":       nid,
            "name":     t["tool_name"],
            "display":  t.get("display_name", t["tool_name"]),
            "service":  t.get("service", ""),
            "risk":     t.get("risk_level", "L1"),
            "category": t.get("category", ""),
            "status":   t.get("status", "draft"),
            "side_effects": t.get("side_effects", "none"),
        }

    # ── Service nodes ─────────────────────────────────────────────
    services = {t.get("service", "") for t in tools if t.get("service")}
    for svc in services:
        nid = f"service:{svc}"
        nodes[nid] = {"type": "service", "id": nid, "name": svc}

    # ── Bundle nodes ──────────────────────────────────────────────
    bundles = {s.get("bundle_scope", "") for s in skills if s.get("bundle_scope")}
    for b in bundles:
        nid = f"bundle:{b}"
        nodes[nid] = {"type": "bundle", "id": nid, "name": b}

    # ── Edges ──────────────────────────────────────────────────────

    # skill → bundle
    for s in skills:
        b = s.get("bundle_scope", "")
        if b:
            edges.append({"src": f"skill:{s['skill_name']}",
                          "dst": f"bundle:{b}", "rel": "in_bundle"})

    # skill → skill (dependencies)
    for s in skills:
        for dep in (s.get("dependencies") or []):
            if dep in skill_map:
                edges.append({"src": f"skill:{s['skill_name']}",
                              "dst": f"skill:{dep}", "rel": "depends_on"})

    # tool → service
    for t in tools:
        svc = t.get("service", "")
        if svc:
            edges.append({"src": f"tool:{t['tool_name']}",
                          "dst": f"service:{svc}", "rel": "belongs_to"})

    # skill → tool  (from called_by_skills reverse mapping)
    tool_consumers: dict[str, list] = {}
    skill_tools:    dict[str, list] = defaultdict(list)

    for t in tools:
        consumers = t.get("called_by_skills") or []
        tool_consumers[t["tool_name"]] = consumers
        for consumer in consumers:
            if consumer in skill_map:
                skill_tools[consumer].append(t["tool_name"])
                edges.append({"src": f"skill:{consumer}",
                              "dst": f"tool:{t['tool_name']}", "rel": "calls"})

    # Additionally scan SKILL.md bodies for inline tool call patterns
    for s in skills:
        path_str = s.get("path", "")
        if path_str:
            skill_path = REPO_ROOT / path_str
            raw_calls = scan_skill_tool_calls(skill_path)
            for call in raw_calls:
                # Convert service:tool_name() → find tool by service+name
                svc_part, fn_part = call.rstrip(")").split(":", 1)
                tool_name_candidate = fn_part.replace("_", "-")
                if tool_name_candidate in tool_map:
                    if tool_name_candidate not in skill_tools[s["skill_name"]]:
                        skill_tools[s["skill_name"]].append(tool_name_candidate)
                        edges.append({"src": f"skill:{s['skill_name']}",
                                      "dst": f"tool:{tool_name_candidate}",
                                      "rel": "calls_inline"})

    # ── Deduplicate edges ─────────────────────────────────────────
    seen = set()
    deduped = []
    for e in edges:
        key = (e["src"], e["dst"], e["rel"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    # ── Build indices ──────────────────────────────────────────────
    skills_by_bundle: dict[str, list] = defaultdict(list)
    for s in skills:
        skills_by_bundle[s.get("bundle_scope", "_unscoped")].append(s["skill_name"])

    tools_by_service: dict[str, list] = defaultdict(list)
    for t in tools:
        tools_by_service[t.get("service", "_unserviced")].append(t["tool_name"])

    return {
        "nodes": nodes,
        "edges": deduped,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(deduped),
            "skills": len(skills),
            "tools":  len(tools),
            "services": len(services),
            "bundles":  len(bundles),
        },
        "index": {
            "skills_by_bundle": dict(skills_by_bundle),
            "tools_by_service": dict(tools_by_service),
            "tool_consumers":   tool_consumers,
            "skill_tools":      dict(skill_tools),
        },
    }


# ─────────────────────────────────────────────
# Queries
# ─────────────────────────────────────────────

def query_orphan_tools(graph: dict, skill_map: dict) -> dict:
    """Tools with no active consuming skills — waste or risk."""
    tool_consumers = graph["index"]["tool_consumers"]
    nodes          = graph["nodes"]
    results        = []

    for tool_name, consumers in tool_consumers.items():
        nid    = f"tool:{tool_name}"
        node   = nodes.get(nid, {})
        status = node.get("status", "")

        if status not in ACTIVE_STATUSES:
            continue   # only check active tools

        active_consumers = [
            c for c in consumers
            if skill_map.get(c, {}).get("status") in ACTIVE_STATUSES
        ]

        if not active_consumers:
            results.append({
                "tool":      tool_name,
                "risk":      node.get("risk", "?"),
                "service":   node.get("service", "?"),
                "consumers": consumers,
                "severity":  "HIGH" if not consumers else "WARNING",
                "note":      "Zero consumers" if not consumers
                             else f"All {len(consumers)} consumer(s) are inactive",
            })

    return {
        "query":   "orphan-tools",
        "count":   len(results),
        "results": sorted(results, key=lambda r: r["risk"], reverse=True),
    }


def query_blast_radius(graph: dict, asset_id: str, skill_map: dict) -> dict:
    """If asset_id changes/breaks, which skills are directly or transitively affected?"""
    tool_consumers = graph["index"]["tool_consumers"]
    nodes          = graph["nodes"]
    edges          = graph["edges"]

    # Normalise: accept "tool:X", "skill:X", or just "X"
    if ":" not in asset_id:
        # Try to resolve
        if f"tool:{asset_id}" in nodes:
            asset_id = f"tool:{asset_id}"
        elif f"skill:{asset_id}" in nodes:
            asset_id = f"skill:{asset_id}"

    if asset_id not in nodes:
        return {"query": "blast-radius", "asset": asset_id,
                "error": f"Asset '{asset_id}' not found in graph"}

    asset_type = nodes[asset_id]["type"]
    affected   = set()

    if asset_type == "tool":
        tool_name  = asset_id.split(":", 1)[1]
        direct = tool_consumers.get(tool_name, [])
        for s in direct:
            affected.add(f"skill:{s}")

    elif asset_type == "skill":
        # Skills that depend on this skill
        for e in edges:
            if e["dst"] == asset_id and e["rel"] == "depends_on":
                affected.add(e["src"])
        # Tools called by this skill (they may expose the skill's blast to upstream)
        for e in edges:
            if e["src"] == asset_id and e["rel"] in ("calls", "calls_inline"):
                affected.add(e["dst"])

    elif asset_type == "service":
        # All tools in this service
        svc_name = asset_id.split(":", 1)[1]
        for e in edges:
            if e["dst"] == asset_id and e["rel"] == "belongs_to":
                tool_id   = e["src"]
                tool_name = tool_id.split(":", 1)[1]
                consumers = tool_consumers.get(tool_name, [])
                for c in consumers:
                    affected.add(f"skill:{c}")
                affected.add(tool_id)

    # Classify by bundle
    by_bundle: dict[str, list] = defaultdict(list)
    affected_details = []
    for nid in sorted(affected):
        n = nodes.get(nid, {})
        bundle = n.get("bundle", "")
        by_bundle[bundle].append(nid)
        affected_details.append({
            "id":     nid,
            "type":   n.get("type", "?"),
            "name":   n.get("name", nid),
            "bundle": bundle,
            "risk":   n.get("risk", "?"),
            "status": n.get("status", "?"),
        })

    return {
        "query":      "blast-radius",
        "asset":      asset_id,
        "asset_type": asset_type,
        "affected_count": len(affected),
        "by_bundle":  dict(by_bundle),
        "affected":   affected_details,
    }


def query_high_risk_chains(graph: dict, skill_map: dict, tool_map: dict) -> dict:
    """Skills whose called tools have HIGHER risk than the skill itself."""
    skill_tools = graph["index"]["skill_tools"]
    nodes       = graph["nodes"]
    results     = []

    for skill_name, tools_called in skill_tools.items():
        skill_node = nodes.get(f"skill:{skill_name}")
        if not skill_node:
            continue
        skill_status = skill_node.get("status", "")
        if skill_status not in ACTIVE_STATUSES:
            continue
        skill_risk_val = RISK_ORDER.get(skill_node.get("risk", "L1"), 1)

        mismatches = []
        for tool_name in tools_called:
            tool_node  = nodes.get(f"tool:{tool_name}")
            if not tool_node:
                continue
            tool_risk  = tool_node.get("risk", "L1")
            tool_risk_val = RISK_ORDER.get(tool_risk, 1)
            if tool_risk_val > skill_risk_val:
                mismatches.append({
                    "tool":      tool_name,
                    "tool_risk": tool_risk,
                    "service":   tool_node.get("service", "?"),
                    "category":  tool_node.get("category", "?"),
                })

        if mismatches:
            results.append({
                "skill":       skill_name,
                "skill_risk":  skill_node.get("risk", "?"),
                "bundle":      skill_node.get("bundle", "?"),
                "max_tool_risk": max(RISK_ORDER.get(m["tool_risk"], 0)
                                     for m in mismatches),
                "mismatches":  mismatches,
                "severity":    "HIGH" if any(RISK_ORDER.get(m["tool_risk"], 0) >= 3
                                             for m in mismatches) else "WARNING",
            })

    results.sort(key=lambda r: r["max_tool_risk"], reverse=True)
    return {
        "query":   "high-risk-chains",
        "count":   len(results),
        "results": results,
    }


def query_bundle_contamination(graph: dict) -> dict:
    """
    Tools called by skills from 2+ different bundles.
    This identifies shared infrastructure vs. bundle-specific tools.
    """
    tool_consumers  = graph["index"]["tool_consumers"]
    nodes           = graph["nodes"]
    results         = []

    for tool_name, consumers in tool_consumers.items():
        tool_node = nodes.get(f"tool:{tool_name}")
        if not tool_node:
            continue
        if tool_node.get("status") not in ACTIVE_STATUSES:
            continue

        bundles_using = defaultdict(list)
        for consumer in consumers:
            skill_node = nodes.get(f"skill:{consumer}")
            if skill_node and skill_node.get("status") in ACTIVE_STATUSES:
                b = skill_node.get("bundle", "_unscoped")
                bundles_using[b].append(consumer)

        if len(bundles_using) >= 2:
            results.append({
                "tool":          tool_name,
                "service":       tool_node.get("service", "?"),
                "risk":          tool_node.get("risk", "?"),
                "bundles_count": len(bundles_using),
                "bundles":       dict(bundles_using),
                "note":          "Shared infrastructure — high coupling"
                                 if len(bundles_using) >= 3 else "Cross-bundle usage",
            })

    results.sort(key=lambda r: r["bundles_count"], reverse=True)
    return {
        "query":   "bundle-contamination",
        "count":   len(results),
        "results": results,
    }


# ─────────────────────────────────────────────
# DOT export
# ─────────────────────────────────────────────

RISK_COLORS = {
    "L0": "#e8f5e9", "L1": "#e3f2fd", "L2": "#fff9c4",
    "L3": "#ffe0b2", "L4": "#ffcdd2",
}
STATUS_BORDER = {
    "approved": "darkgreen", "restricted": "darkorange",
    "deprecated": "gray", "retired": "lightgray",
    "draft": "steelblue", "submitted": "steelblue", "needs_revision": "red",
}


def export_dot(graph: dict) -> str:
    nodes  = graph["nodes"]
    edges  = graph["edges"]
    index  = graph["index"]

    lines = [
        "digraph AssetGraph {",
        '  rankdir=LR;',
        '  graph [fontname="Arial" fontsize=12 bgcolor="#fafafa"];',
        '  node  [fontname="Arial" fontsize=10];',
        '  edge  [fontname="Arial" fontsize=9 color="#555555"];',
        "",
    ]

    # Bundle clusters
    for bundle, skill_names in index["skills_by_bundle"].items():
        bid = bundle.replace("-", "_")
        lines.append(f'  subgraph cluster_{bid} {{')
        lines.append(f'    label="{bundle}";')
        lines.append(f'    style=filled; fillcolor="#f0f4ff"; color=steelblue;')
        for s in skill_names:
            n = nodes.get(f"skill:{s}", {})
            risk   = n.get("risk", "L1")
            status = n.get("status", "draft")
            fill   = RISK_COLORS.get(risk, "#ffffff")
            border = STATUS_BORDER.get(status, "black")
            label  = f'{s}\\n[{risk}]'
            lines.append(
                f'    "skill:{s}" [label="{label}" shape=box '
                f'style="filled,rounded" fillcolor="{fill}" color="{border}"];'
            )
        lines.append("  }\n")

    # Tool nodes (grouped loosely by service)
    lines.append("  // Tools")
    for svc, tool_names in index["tools_by_service"].items():
        lines.append(f'  // service: {svc}')
        for t in tool_names:
            n = nodes.get(f"tool:{t}", {})
            risk   = n.get("risk", "L1")
            status = n.get("status", "draft")
            fill   = RISK_COLORS.get(risk, "#ffffff")
            border = STATUS_BORDER.get(status, "black")
            label  = f'{t}\\n[{risk}] {svc}'
            lines.append(
                f'  "tool:{t}" [label="{label}" shape=ellipse '
                f'style="filled" fillcolor="{fill}" color="{border}"];'
            )
    lines.append("")

    # Service nodes
    lines.append("  // Services")
    for nid, n in nodes.items():
        if n["type"] == "service":
            lines.append(
                f'  "{nid}" [label="{n["name"]}" shape=diamond '
                f'style="filled" fillcolor="#e0e0e0" color="#555555"];'
            )
    lines.append("")

    # Edges (exclude in_bundle to reduce clutter; show calls and depends_on)
    lines.append("  // Edges")
    edge_styles = {
        "calls":        '[color="#2196f3" penwidth=1.5]',
        "calls_inline": '[color="#90caf9" style=dashed]',
        "depends_on":   '[color="#ff9800" style=dashed penwidth=1.5]',
        "belongs_to":   '[color="#9e9e9e" style=dotted]',
    }
    for e in edges:
        rel = e["rel"]
        if rel == "in_bundle":
            continue   # captured by cluster
        style = edge_styles.get(rel, "")
        lines.append(f'  "{e["src"]}" -> "{e["dst"]}" {style};')

    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Human-readable summary
# ─────────────────────────────────────────────

def print_summary(graph: dict):
    s = graph["stats"]
    idx = graph["index"]
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Asset Graph Summary")
    print(f"{sep}\n")
    print(f"  Nodes: {s['total_nodes']}   Edges: {s['total_edges']}")
    print(f"  Skills: {s['skills']}   Tools: {s['tools']}   "
          f"Services: {s['services']}   Bundles: {s['bundles']}")
    print()

    print("  Bundles:")
    for bundle, skills in sorted(idx["skills_by_bundle"].items()):
        print(f"    {bundle:<25} {len(skills):>2} skills")
    print()

    print("  Services:")
    for svc, tools in sorted(idx["tools_by_service"].items()):
        print(f"    {svc:<25} {len(tools):>2} tools")
    print()

    # Connectivity stats
    no_tools = [s for s, t in idx["skill_tools"].items() if not t]
    print(f"  Skills with no tool calls : {len(no_tools)}")
    zero_consumers = [t for t, c in idx["tool_consumers"].items() if not c]
    print(f"  Tools with zero consumers : {len(zero_consumers)}")
    print(f"{sep}\n")


def print_query_result(result: dict):
    q = result.get("query", "?")
    sep = "-" * 60

    if "error" in result:
        print(f"\n[ERROR] {result['error']}\n")
        return

    print(f"\n{sep}")
    print(f"  Query: {q}   Findings: {result.get('count', len(result.get('results', [])))}")
    print(f"{sep}\n")

    items = result.get("results") or result.get("affected") or []

    if q == "orphan-tools":
        for r in items:
            sev = "[HH]" if r["severity"] == "HIGH" else "[WW]"
            print(f"  {sev} tool:{r['tool']:<40} risk={r['risk']}  svc={r['service']}")
            print(f"       {r['note']}")
        if not items:
            print("  [OK] No orphan tools found.\n")

    elif q == "blast-radius":
        print(f"  Asset:    {result['asset']}")
        print(f"  Affected: {result['affected_count']} node(s)\n")
        for bundle, nids in result.get("by_bundle", {}).items():
            print(f"  Bundle: {bundle}")
            for nid in nids:
                n = next((x for x in items if x["id"] == nid), {})
                print(f"    - {nid}  risk={n.get('risk','?')}  status={n.get('status','?')}")
        if not items:
            print("  No affected nodes found.\n")

    elif q == "high-risk-chains":
        for r in items:
            sev = "[HH]" if r["severity"] == "HIGH" else "[WW]"
            print(f"  {sev} skill:{r['skill']:<40} risk={r['skill_risk']}  bundle={r['bundle']}")
            for m in r["mismatches"]:
                print(f"       calls tool:{m['tool']:<35} risk={m['tool_risk']}")
        if not items:
            print("  [OK] No risk inheritance gaps found.\n")

    elif q == "bundle-contamination":
        for r in items:
            print(f"  tool:{r['tool']:<40} risk={r['risk']}  bundles={r['bundles_count']}")
            for bundle, skills in r["bundles"].items():
                print(f"       {bundle}: {skills}")
        if not items:
            print("  [OK] No cross-bundle tool sharing found.\n")

    print()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Asset Dependency Graph")
    parser.add_argument("--skill-registry", default="skill-registry.yaml")
    parser.add_argument("--tool-registry",  default="tool-registry.yaml")
    parser.add_argument("--query", choices=[
        "orphan-tools", "blast-radius", "high-risk-chains",
        "bundle-contamination", "summary",
    ], default="summary", help="Query to run (default: summary)")
    parser.add_argument("--asset", help="Asset ID for blast-radius query (e.g. tool:parse-business-intent)")
    parser.add_argument("--output", help="Write full graph JSON to this path")
    parser.add_argument("--dot",    help="Write Graphviz DOT file to this path")
    parser.add_argument("--json",   action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    skill_path = Path(args.skill_registry)
    tool_path  = Path(args.tool_registry)
    for p in (skill_path, tool_path):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(2)

    skill_data = load_yaml(skill_path)
    tool_data  = load_yaml(tool_path)

    skill_map = {s["skill_name"]: s for s in skill_data.get("skills", [])}
    tool_map  = {t["tool_name"]:  t for t in tool_data.get("tools",   [])}

    graph = build_graph(skill_data, tool_data)

    # ── DOT export ────────────────────────────────────────────────
    if args.dot:
        dot = export_dot(graph)
        Path(args.dot).parent.mkdir(parents=True, exist_ok=True)
        Path(args.dot).write_text(dot, encoding="utf-8")
        print(f"DOT graph written to {args.dot}")
        print("Render online: https://dreampuf.github.io/GraphvizOnline/")

    # ── Full graph JSON ───────────────────────────────────────────
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"Graph JSON written to {args.output}")

    # ── Query ─────────────────────────────────────────────────────
    if args.query == "summary" or (not args.query):
        print_summary(graph)
        if args.json:
            print(json.dumps(graph["stats"], indent=2, ensure_ascii=False))
        return

    if args.query == "orphan-tools":
        result = query_orphan_tools(graph, skill_map)
    elif args.query == "blast-radius":
        if not args.asset:
            print("ERROR: --asset required for blast-radius query", file=sys.stderr)
            sys.exit(2)
        result = query_blast_radius(graph, args.asset, skill_map)
    elif args.query == "high-risk-chains":
        result = query_high_risk_chains(graph, skill_map, tool_map)
    elif args.query == "bundle-contamination":
        result = query_bundle_contamination(graph)
    else:
        print(f"Unknown query: {args.query}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_query_result(result)

    has_findings = result.get("count", 0) > 0 or result.get("affected_count", 0) > 0
    sys.exit(1 if has_findings else 0)


if __name__ == "__main__":
    main()
