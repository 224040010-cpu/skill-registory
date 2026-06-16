---
name: building-portfolio-knowledge-graph
description: |
  Rebuilds the stock_monitor portfolio knowledge graph by running the local
  pipeline (ingest, compression LLM-wiki, and typed networkx graph build) and
  produces refreshed graph.json, per-entity wiki pages, and graph metrics.
  Use when a request asks to build, rebuild, or refresh the portfolio knowledge
  graph, the LLM-wiki, or the "portfolio brain", or after holdings/news data
  changes and the graph is stale.
  Do NOT use when the request only wants to read existing discovery results
  (route to discovering-portfolio-alpha) or ask a question of the brain
  (route to querying-portfolio-brain).
---

# Purpose

This skill refreshes the portfolio "second brain". It normalizes the project's
own research artifacts into knowledge documents, compresses them into linked
wiki pages with a local LLM, and builds a typed knowledge graph that later
stages mine for hidden cross-ticker relationships. It exists so an orchestrating
agent can keep the graph current before discovery or Q&A runs.

---

# Trigger

**Use this Skill when:**
- A request says "rebuild the knowledge graph", "refresh the portfolio brain", or "update the LLM-wiki"
- Holdings, watchlist, or news caches have changed and the graph is stale
- A weekly maintenance run needs to regenerate graph artifacts
- An orchestrator needs fresh `graph.json` + wiki pages before discovery

**Do NOT use this Skill when:**
- The request only wants to read the ranked candidate-alpha report — route to `discovering-portfolio-alpha`
- The request is a natural-language question about the portfolio — route to `querying-portfolio-brain`

---

# Workflow

[ ] Step 1: Run the build pipeline
    - Call `data-pipeline-mcp:run_script(script="src.knowledge.pipeline", args={"no_llm": false})`
    - This runs ingest -> compress -> graph -> discovery -> gap -> evolution in order
    - Read the returned per-stage report; confirm `ingest`, `compress`, and `graph` stages report `ok: true`

[ ] Step 2: Verify the graph artifacts exist
    - Call `file-system-mcp:list_files(path="data/knowledge/graph", pattern="*.json")`
    - Confirm `graph.json` and `metrics.json` are present and recently modified
    - Read `metrics.json` and surface node/edge/theme counts as the result

[ ] Step 3: Report the outcome
    - Return a summary: number of nodes, edges, themes, and the wiki page count
    - Include the artifact paths produced under `data/knowledge/`

**Error handling:**
- If the local LLM is unreachable → re-run with `args={"no_llm": true}` so compression falls back to deterministic summaries, and note the degraded mode in the result
- If `run_script` returns `success: false` → return the captured `output` and stop; do not fabricate metrics
- If no graph files are found in Step 2 → report the build did not complete and surface the pipeline error

---

# References

- Pipeline stage descriptions and output layout: See `references/pipeline-overview.md`

---

# Scripts

**src.knowledge.pipeline** — orchestrates the full knowledge build
- Execute: `python -m src.knowledge.pipeline` (add `--no-llm` for deterministic mode)
- Input: reads holdings/news from the stock_monitor config and caches
- Output: writes `data/knowledge/{docs,wiki,graph,discovery,gap,evolution}` and prints a per-stage JSON report

---

# Constraints

- NEVER invent node or edge counts — report only values read from `metrics.json`
- NEVER act on the graph as a trade signal; outputs are research finders only
- This skill is WRITE scope (L3) — it writes regenerable artifacts under `data/knowledge/` and never touches live accounts or devices
- Data access is limited to the stock_monitor project's own config and local caches
- Output must include ALL of the following fields:
  1. status (ok / degraded / failed)
  2. node_count, edge_count, theme_count
  3. artifact paths written under data/knowledge/
- Example result: `{ "status": "ok", "node_count": 41, "edge_count": 43, "theme_count": 7 }`. Edge case: if the build fails, return `{ "status": "failed", "error": "<pipeline output>" }`.
