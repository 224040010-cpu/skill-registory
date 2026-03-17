# Skill Generation Anti-Patterns

Patterns that indicate skill generation has gone wrong — and how to catch them
during `capability-planning` before they reach `guiding-skill-authoring`.

---

## Anti-Pattern 1: Pipeline Leakage

**What it looks like:**
Each step in a sequential pipeline becomes its own skill.

```
extract-text → parse-entities → map-elements → assemble-model → serialize-xml
```
All five become SKILL.md files.

**Why it's wrong:**
Steps 1–4 have no independent trigger. Users never ask for _only_ step 3.
The pipeline is an implementation detail of a larger skill or workflow.

**Detection (Self-Critique Check C):**
Does each skill's trigger *require* the output of the previous skill?
If yes → it's a pipeline, not a skill set. Collapse into one skill or
move to agent workflow layer.

**Fix:**
- Identify which single step is independently triggerable → that's the skill
- Everything before it = data preparation tools
- Everything after it = post-processing tools or workflow steps

---

## Anti-Pattern 2: CRUD Explosion

**What it looks like:**
One entity type → four skills (Create, Read, Update, Delete).

```
creating-work-order
reading-work-order
updating-work-order
deleting-work-order
```

**Why it's wrong:**
Read/Write/Delete on the same entity are usually the same skill with
different operations, or they're MCP Tool wrappers, not skills at all.

**Detection (Self-Critique Check B):**
> 70% description overlap, same entity, different verb.

**Fix:**
- If each operation requires distinct multi-step reasoning → keep separate
- If each operation is a single atomic call → collapse to MCP Tools
- Most common: one skill `managing-work-orders` + 4 tools underneath it

---

## Anti-Pattern 3: Qualifier Proliferation

**What it looks like:**
The same capability replicated for each domain variant.

```
analyzing-ev-charger-faults
analyzing-solar-panel-faults
analyzing-pump-faults
analyzing-hvac-faults
```

**Why it's wrong:**
One parameterized skill handles all domains. Separate skills create
routing conflicts (all trigger on "analyze faults") and multiply
maintenance burden.

**Detection (Self-Critique Check B):**
Same verb + same abstract noun, different domain qualifier.

**Fix:**
One skill `analyzing-equipment-faults` with a `device_type` input parameter.
Domain specialization belongs in tool parameters or knowledge files, not skill names.

---

## Anti-Pattern 4: Wrapper Skills

**What it looks like:**
A skill whose entire workflow is one tool call:

```yaml
# Workflow
[ ] Step 1: Call `data-service:get_user_profile(user_id)`
[ ] Step 2: Return the result
```

**Why it's wrong:**
This is an MCP Tool with extra steps. Creating a SKILL.md adds registry
weight and routing overhead for no reasoning value.

**Detection (Self-Critique Check A):**
≤ 1 step + no error handling + no conditional logic.

**Fix:**
Remove the SKILL.md. Register `data-service:get_user_profile` as an MCP Tool.
Skills that need this data call the tool directly.

---

## Anti-Pattern 5: God Skill

**What it looks like:**
One skill that does everything.

```
description: Converts any business input into BPMN by parsing, extracting,
  mapping, assembling, optimizing, validating, and serializing. Use when
  anything related to BPMN is needed.
```

**Why it's wrong:**
The trigger is impossibly broad → routing conflicts with every BPMN-adjacent
skill. The workflow is too long → error recovery is intractable.

**Detection:**
Description contains "any", "all", "everything", or a comma-separated list
of 4+ distinct operations. Trigger is ≥ 3 lines of "use when".

**Fix:**
Decompose: identify the core multi-step reasoning unit that needs a skill.
Everything else becomes tools and workflow steps around it.

---

## Anti-Pattern 6: Premature Specialization

**What it looks like:**
A skill scoped so narrowly it will only ever fire once.

```
converting-q3-2024-procurement-reports-to-bpmn
```

**Why it's wrong:**
Skills are durable, reusable reasoning units. Time-specific or project-specific
scoping means the skill becomes dead weight after one use.

**Detection:**
Skill name contains dates, project codes, sprint numbers, or customer names.

**Fix:**
Generalize the skill. Move specifics to input parameters or knowledge files.
`converting-procurement-report-to-bpmn` handles all quarters.

---

## Summary Checklist

Before approving a capability plan, confirm:

- [ ] No skill in the plan is purely a sequential pipeline step (Anti-Pattern 1)
- [ ] No entity type produces more than 2 skills (Anti-Pattern 2)
- [ ] No capability name family uses the same verb+noun with only domain qualifiers (Anti-Pattern 3)
- [ ] No skill's workflow has ≤ 1 step and no error handling (Anti-Pattern 4)
- [ ] No skill description contains "any" or lists 4+ distinct operations (Anti-Pattern 5)
- [ ] No skill name contains time, project, sprint, or customer specifics (Anti-Pattern 6)
