---
name: querying-portfolio-brain
description: |
  Answers a natural-language question about the stock_monitor portfolio by
  running retrieval-augmented generation over the knowledge wiki and documents,
  returning a grounded answer with its supporting sources and a research-only
  disclaimer.
  Use when a request poses a question about the portfolio's structure, themes,
  signals, or hidden relationships, or asks to "chat with the portfolio brain".
  Do NOT use when the request asks to rebuild the graph (route to
  building-portfolio-knowledge-graph) or wants the ranked discovery report
  (route to discovering-portfolio-alpha).
---

# Purpose

This skill lets an analyst interrogate the portfolio "second brain" in natural
language. It runs a retrieval-augmented query over the compressed wiki pages and
knowledge documents and returns an answer grounded in the project's own data,
always carrying the sources it used and a research-only disclaimer.

---

# Trigger

**Use this Skill when:**
- A request is a question like "what links my AI and energy holdings?"
- A user wants to "ask the portfolio brain" or "chat with the knowledge graph"
- An orchestrator routes a free-text research query to the knowledge layer
- A user asks why two names are connected in the graph

**Do NOT use this Skill when:**
- The request asks to rebuild or refresh the graph — route to `building-portfolio-knowledge-graph`
- The request wants the ranked candidate-alpha list — route to `discovering-portfolio-alpha`

---

# Workflow

[ ] Step 1: Confirm the knowledge base exists
    - Call `file-system-mcp:list_files(path="data/knowledge/docs", pattern="knowledge.jsonl")`
    - If absent → stop and report the brain must be built first

[ ] Step 2: Run the dialogue query
    - Call `data-pipeline-mcp:run_script(script="src.knowledge.dialogue", args={"query": "<the user question>"})`
    - This builds/loads the RAG index over wiki + docs and answers the query
    - Capture the returned answer and its sources list

[ ] Step 3: Return the grounded answer
    - Return the answer text, the sources used, and the research-only disclaimer

**Error handling:**
- If Step 1 finds no `knowledge.jsonl` → return "brain not built" and point to the build skill; do not answer from general knowledge
- If the local LLM or vector store is unreachable → return a clear unavailable message, not a hallucinated answer
- If retrieval returns no sources → state that the brain has no evidence on the query rather than guessing

---

# References

- Dialogue response shape: See `references/ask-example.md`

---

# Scripts

**src.knowledge.dialogue** — RAG Q&A over the knowledge base
- Execute: `python -m src.knowledge.dialogue "<question>"`
- Input: a natural-language query string
- Output: returns `{question, answer, sources, disclaimer}`

---

# Constraints

- NEVER answer from outside the retrieved context — if the brain lacks evidence, say so
- NEVER drop the research-only disclaimer from the response
- This skill is READ-ONLY analysis (L2) — it reads the knowledge base and the local vector index and never modifies holdings or places orders
- Data access is limited to the local `data/knowledge/` wiki and documents
- Output must include ALL of the following fields:
  1. answer
  2. sources (entities/documents used)
  3. disclaimer (research-only)
- Example query "What links NVDA and energy names?" returns an answer plus sources such as the `ai` and `semiconductor` wiki pages. Edge case: a query with no matching evidence returns an explicit "no evidence" response.
