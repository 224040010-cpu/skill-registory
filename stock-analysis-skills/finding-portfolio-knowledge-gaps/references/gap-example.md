# Gap output (example)

The gap stage analyzes graph coverage and emits `suggestions.json`:

```json
{
  "as_of": "2026-06-16",
  "suggested_tickers": ["TSM", "ALB", "ABBV"],
  "gaps": {
    "_source": "llm",
    "missing_tickers": [{"ticker": "TSM", "reason": "key foundry supplier not yet linked"}],
    "missing_themes": [{"theme": "memory", "reason": "HBM bottleneck under-covered"}],
    "missing_factors": [{"factor": "power grid capacity", "reason": "AI data-center constraint"}]
  }
}
```

## Heuristic fallback

If the LLM is unreachable or returns unparsable output, the stage falls back to
a deterministic heuristic: it suggests universe tickers not yet present in the
graph and flags themes with only one linked member. The result then reports
`_source: heuristic`.
