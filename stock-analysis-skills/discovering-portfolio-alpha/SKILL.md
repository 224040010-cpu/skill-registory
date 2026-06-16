---
name: discovering-portfolio-alpha
description: |
  Ranks non-obvious relationships in the stock_monitor knowledge graph as
  candidate alpha by scoring links on non-obviousness, signal-agreement, and
  freshness, then attaches a local-LLM rationale to each, producing a ranked
  discovery report.
  Use when a request asks for hidden links, candidate alpha, non-obvious
  connections between holdings, or which relationships in the portfolio are
  worth researching next.
  Do NOT use when the graph has not been built yet (route to
  building-portfolio-knowledge-graph) or when the request asks what factors are
  missing (route to finding-portfolio-knowledge-gaps).
---

# Purpose

This skill surfaces the "unknown-knowns" — relationships already present in the
portfolio's data that an analyst has not noticed. It reads the persisted
knowledge graph, ranks ticker-to-ticker links by a transparent score, and
explains each candidate so a human can decide what to research next.

---

# Trigger

**Use this Skill when:**
- A request says "find hidden links", "what's the candidate alpha", or "non-obvious connections"
- An orchestrator needs the ranked discovery report after a graph rebuild
- A weekly run wants the top candidate relationships surfaced
- A user asks "what in my portfolio should I research?"

**Do NOT use this Skill when:**
- No `graph.json` exists yet — route to `building-portfolio-knowledge-graph` first
- The request asks what tickers/themes are missing — route to `finding-portfolio-knowledge-gaps`

---

# Workflow

[ ] Step 1: Confirm the graph exists
    - Call `file-system-mcp:list_files(path="data/knowledge/graph", pattern="graph.json")`
    - If absent → stop and report that the graph must be built first

[ ] Step 2: Run the discovery stage
    - Call `data-pipeline-mcp:run_script(script="src.knowledge.discovery", args={"no_llm": false})`
    - This scores links and writes `data/knowledge/discovery/latest.json` and `latest.md`
    - Confirm the returned `count` of candidates is greater than zero

[ ] Step 3: Return the ranked report
    - Read `data/knowledge/discovery/latest.json`
    - Return the top candidates with pair, score, edge types, and rationale

**Error handling:**
- If Step 1 finds no graph file → return "graph not built" and point to the build skill; do not run discovery
- If the local LLM is unreachable → re-run with `args={"no_llm": true}` to produce the ranked report without rationale text, and note the degraded mode
- If `run_script` returns `success: false` → surface the captured `output` and stop

---

# References

- Scoring formula and field meanings: See `references/scoring-example.md`

---

# Scripts

**src.knowledge.discovery** — ranks candidate-alpha links
- Execute: `python -m src.knowledge.discovery` (add `--no-llm` to skip rationale)
- Input: reads `data/knowledge/graph/graph.json` and `docs/knowledge.jsonl`
- Output: writes `data/knowledge/discovery/latest.{json,md}` and prints a count

---

# Constraints

- NEVER present a candidate relationship as a buy/sell recommendation — these are research finders only
- NEVER invent scores or rationales; return only values produced by the discovery stage
- This skill is READ-ONLY analysis (L2) over already-built artifacts — it reads the graph and writes only the discovery report
- Data access is limited to the local `data/knowledge/` artifacts
- Output must include ALL of the following fields:
  1. as_of date
  2. ranked candidates (pair, score, edge_types)
  3. rationale per candidate (or a degraded-mode note if the LLM was unavailable)
- Example result row: `{ "pair": ["NVDA", "EQT"], "score": 0.82, "edge_types": ["co_mentioned"] }`. Edge case: if no candidates are found, return an empty list with an explanatory note.
