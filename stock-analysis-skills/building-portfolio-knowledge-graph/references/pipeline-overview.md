# Knowledge pipeline overview (example artifacts)

The `src.knowledge.pipeline` module runs six stages in order. This skill cares
about the first three (the build); later stages are owned by sibling skills.

| Stage | Module | Output |
|---|---|---|
| ingest | `src.knowledge.ingest` | `data/knowledge/docs/knowledge.jsonl` |
| compress | `src.knowledge.compress` | `data/knowledge/wiki/<type>/<name>.md` + `wiki/index.json` |
| graph | `src.knowledge.graph_build` | `data/knowledge/graph/{graph.json,graph.gexf,metrics.json}` |

## Example `metrics.json`

```json
{ "num_nodes": 41, "num_edges": 43, "num_tickers": 34, "num_themes": 7,
  "density": 0.0524, "components": 25, "avg_degree": 2.098 }
```

## Degraded mode

When the local LLM is unreachable, run with `--no-llm`. Compression then writes
deterministic extractive summaries instead of LLM summaries; the graph build is
unaffected. The result should flag `status: degraded`.
