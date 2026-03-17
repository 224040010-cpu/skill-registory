# Capability Classification Guide

Extended examples for the skill / tool / workflow_step decision tree in `capability-planning`.

---

## The Three Types at a Glance

| Dimension | skill | tool | workflow_step |
|---|---|---|---|
| **Independently triggerable?** | Yes | Yes | No |
| **Multi-step / conditional?** | Yes | No | Either |
| **Reusable across agents?** | Yes | Yes | No |
| **Has a trigger sentence?** | Yes | Yes (implicit) | No |
| **Implemented as** | SKILL.md | MCP server function | Agent workflow YAML |
| **Discoverable by router?** | Yes | Via skill's tool list | No |

---

## Worked Examples

### Example A: "把业务描述转换成 BPMN 并优化流程"

Raw decomposition:

| # | Raw capability | Decision |
|---|---|---|
| 1 | Parse business description into sentences | **tool** — single deterministic parse, no branching |
| 2 | Extract named entities (roles, systems, actions) | **tool** — atomic NLP transform |
| 3 | Map entities to BPMN element types | **workflow_step** — only triggered as part of a larger BPMN generation sequence, not independently |
| 4 | Assemble BPMN model from mapped elements | **workflow_step** — same, cannot be independently triggered |
| 5 | Detect parallelizable steps and restructure as gateways | **skill** — a user might say "optimize this BPMN for parallel execution" independently |
| 6 | Serialize final BPMN to XML | **tool** — deterministic formatting step |

**Result:** 1 skill (`optimizing-bpmn-workflow`), 3 tools, 2 workflow_steps.
**Before planning:** might have generated 6 skills. **After:** 1 well-scoped skill.

---

### Example B: "故障诊断Agent"

Raw decomposition:

| # | Raw capability | Decision |
|---|---|---|
| 1 | Query charger fault logs | **tool** — single read, deterministic |
| 2 | Correlate fault codes with known error library | **skill** — multi-step, conditional (severity branching), independently triggerable ("帮我分析这个故障") |
| 3 | Generate maintenance recommendation | **skill** — user might ask "给我一个维修建议" independently |
| 4 | Notify maintenance team | **tool** — single webhook call |
| 5 | Create work order | **skill** — multi-step form filling + submission, reusable |

**Result:** 3 skills, 2 tools.

---

### Example C: Over-fragmented bundle (self-critique catch)

A submitter proposed 8 skills for "entity extraction pipeline":

- `extract-person-names`
- `extract-organization-names`
- `extract-location-names`
- `extract-date-expressions`
- `extract-monetary-amounts`
- `extract-product-codes`
- `validate-extracted-entities`
- `deduplicate-entity-list`

**Self-Critique Check B** fires: all extraction skills overlap > 70%.  
**Self-Critique Check A** fires: each has ≤ 1 step.  

**Action:** Merge all extraction items → one tool `extract-entities` (MCP Tool).  
`validate-extracted-entities` → tool.  
`deduplicate-entity-list` → tool.  
**Result:** 0 skills, 3 tools. None needed a SKILL.md.

---

## Common Misclassifications

### "It has steps, so it must be a skill"

Wrong. A step-count alone does not make something a skill.  
Ask: **Can a user independently say "do only this"?**

`map-entities-to-bpmn-elements` — even if it has 3 internal steps, a user will
never ask for _only_ entity mapping. It's always part of a larger BPMN task.
→ `workflow_step`

### "It's reusable, so it must be a skill"

Wrong. Reusability is necessary but not sufficient.  
Also require: independent trigger + multi-step reasoning.

`parse-text-to-sentences` is reusable and single-step.
→ `tool`

### "It uses an LLM, so it must be a skill"

Wrong. Some LLM calls are deterministic single-pass transforms (classify, format,
translate). If there's no branching or context accumulation:
→ `tool`

---

## Decision Shortcuts

When uncertain, ask:

> "Could a user in a fresh conversation say: 'Hey, just do [this capability]
> for me' and get useful standalone value?"

If **yes** and it requires reasoning → `skill`  
If **yes** but it's a single operation → `tool`  
If **no** → `workflow_step`
