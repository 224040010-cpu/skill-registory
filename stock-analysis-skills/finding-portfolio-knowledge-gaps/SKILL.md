---
name: finding-portfolio-knowledge-gaps
description: |
  Analyzes the stock_monitor knowledge graph for blind spots and produces a
  ranked list of missing tickers, themes, and macro factors (the
  unknown-unknowns) plus a suggestions file that can feed back into the next
  ingest cycle.
  Use when a request asks what the portfolio is missing, what to add next, what
  blind spots or under-covered themes exist, or asks for gap analysis of the
  portfolio brain.
  Do NOT use when the request wants existing hidden links (route to
  discovering-portfolio-alpha) or wants to rebuild the graph (route to
  building-portfolio-knowledge-graph).
---

# Purpose

This skill closes the discovery loop by finding what is absent. It examines the
graph's coverage and asks a local LLM (with a deterministic heuristic fallback)
which adjacent tickers, supply-chain factors, and themes would complete the
picture, writing machine-readable suggestions the ingest stage can consume next.

---

# Trigger

**Use this Skill when:**
- A request says "what am I missing", "find blind spots", or "gap analysis"
- An orchestrator wants suggested new tickers/themes after discovery runs
- A weekly run wants to refresh the unknown-unknowns report
- A user asks "what should I add to my coverage?"

**Do NOT use this Skill when:**
- The request wants existing non-obvious links — route to `discovering-portfolio-alpha`
- The graph is missing and must first be rebuilt — route to `building-portfolio-knowledge-graph`

---

# Workflow

[ ] Step 1: Confirm the graph exists
    - Call `file-system-mcp:list_files(path="data/knowledge/graph", pattern="graph.json")`
    - If absent → stop and report that the graph must be built first

[ ] Step 2: Run the gap stage
    - Call `data-pipeline-mcp:run_script(script="src.knowledge.gap", args={"no_llm": false})`
    - This writes `data/knowledge/gap/latest.md` and `suggestions.json`
    - Note whether the result `source` is `llm` or `heuristic`

[ ] Step 3: Return the suggestions
    - Read `data/knowledge/gap/suggestions.json`
    - Return suggested missing tickers (with reasons) and under-covered themes

**Error handling:**
- If Step 1 finds no graph file → return "graph not built" and point to the build skill
- If the local LLM is unreachable → the stage falls back to the deterministic heuristic automatically; report `source: heuristic`
- If `run_script` returns `success: false` → surface the captured `output` and stop

---

# References

- Gap output shape and heuristic fallback: See `references/gap-example.md`

---

# Scripts

**src.knowledge.gap** — finds missing tickers/themes/factors
- Execute: `python -m src.knowledge.gap` (add `--no-llm` to force the heuristic)
- Input: reads `data/knowledge/graph/graph.json`
- Output: writes `data/knowledge/gap/{latest.md,suggestions.json}`

---

# Constraints

- NEVER present a suggested ticker as a recommendation to buy — suggestions are research directions only
- NEVER invent suggestions; return only what the gap stage produced
- This skill is READ-ONLY analysis (L2) over the built graph — it reads the graph and writes only the gap report
- Data access is limited to the local `data/knowledge/` artifacts
- Output must include ALL of the following fields:
  1. source (llm or heuristic)
  2. suggested_tickers (with reasons)
  3. missing_themes / missing_factors
- Example result: `{ "source": "llm", "suggested_tickers": ["TSM", "ALB"] }`. Edge case: if no gaps are found, return empty suggestion lists with a note.
