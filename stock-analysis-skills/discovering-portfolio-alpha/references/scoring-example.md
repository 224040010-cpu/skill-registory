# Discovery scoring (example)

Each ticker-to-ticker link is scored:

```
score = w_nonobvious * non_obviousness
      + w_agreement  * signal_agreement
      + w_freshness  * freshness
```

Default weights (from `config/portfolio.yaml` → `knowledge.discovery`):
`w_nonobvious=0.5`, `w_agreement=0.3`, `w_freshness=0.2`.

- **non_obviousness**: `1 - theme_overlap`, boosted when the only link is a
  cross-signal mechanism (news co-mention, correlation, signal agreement).
- **signal_agreement**: 1.0 if both verdicts align, 0.6 correlated, 0.4 co-mention.
- **freshness**: recency of the supporting news/verdict/opportunity evidence.

## Example candidate

```json
{ "pair": ["NVDA", "EQT"], "score": 0.82, "non_obviousness": 1.0,
  "signal_agreement": 0.4, "freshness": 1.0, "edge_types": ["co_mentioned"],
  "rationale": "Both ride AI data-center power demand..." }
```

Membership edges (ticker-to-theme) are excluded — only ticker-to-ticker links
are candidate alpha.
