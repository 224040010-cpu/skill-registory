# Dialogue response (example)

`src.knowledge.dialogue` runs RAG over the wiki + docs and returns:

```json
{
  "question": "What links my AI and energy holdings?",
  "answer": "NVDA and EQT both benefit from AI data-center power demand ...",
  "sources": [
    {"kind": "wiki", "entity": "ai", "source": "data/knowledge/wiki/theme/ai.md"},
    {"kind": "theme", "entity": "AMD,NVDA,EQT", "source": "theme_map"}
  ],
  "disclaimer": "This answer is a research finder from your knowledge graph, not financial advice. Run the daily verdict/audit pipeline before acting."
}
```

The disclaimer is mandatory on every answer. If no sources are retrieved, the
answer must state that the brain has no evidence on the query.
