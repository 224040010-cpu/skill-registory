# business-to-bpmn Tool Catalog

These 13 capabilities were reclassified from SKILL.md files to MCP Tool requests
during the capability-planning pass on 2026-03-17.

**Why tools, not skills?** Each entry failed the three-gate skill test:
- Either non-independently-triggerable (primary trigger was "currently at pipeline layer X")
- Or single-step deterministic operation (no multi-step reasoning/branching)
- Or algorithmic transform (no context accumulation across turns)

All three skills in this bundle (`converting-business-to-bpmn`,
`decomposing-business-process`, `validating-bpmn-compliance`) call these tools.

---

## Tool Requests

### T-01: `parse-business-intent`

**Source skill removed:** `intent-parser/SKILL.md`  
**What it does:** Parses a natural language business description into structured intent JSON.  
**Risk level:** L1 (read-only NLP)

**Input:**
```json
{ "user_description": "string" }
```

**Output:**
```json
{
  "business_type": "approval|alert-handling|data-sync|order-processing|reporting|...",
  "goal": "string",
  "constraints": ["string"],
  "scope": "string"
}
```

---

### T-02: `extract-process-entities`

**Source skill removed:** `entity-extractor/SKILL.md`  
**What it does:** Extracts roles, systems, data objects, and trigger events from description + intent.  
**Risk level:** L1

**Input:**
```json
{ "user_description": "string", "intent": "IntentOutput" }
```

**Output:**
```json
{
  "roles": [{ "id": "role_1", "name": "string", "description": "string" }],
  "systems": [...],
  "data_objects": [...],
  "triggers": [...]
}
```

---

### T-03: `detect-description-ambiguity`

**Source skill removed:** `ambiguity-detector/SKILL.md`  
**What it does:** Checks intent + entities for ambiguities, outputs clarification questions.  
**Risk level:** L2 (analytical)

**Input:**
```json
{ "intent": "IntentOutput", "entities": "EntityOutput" }
```

**Output:**
```json
{
  "has_ambiguity": true,
  "ambiguity_points": [{ "type": "string", "description": "string", "affected_entities": ["string"] }],
  "clarification_questions": ["string"]
}
```

---

### T-04: `match-bpmn-template`

**Source skill removed:** `bpmn-template-matcher/SKILL.md`  
**What it does:** Looks up BPMN workflow template library by intent, returns top-3 matches with similarity scores.  
**Risk level:** L1

**Known template categories:** `approval`, `alert-handling`, `data-sync`, `order-processing`, `reporting`, `onboarding`

**Input:**
```json
{ "intent": "IntentOutput" }
```

**Output:**
```json
{
  "candidates": [{ "template_id": "string", "template_name": "string", "similarity_score": 0.85, "description": "string" }],
  "best_match": { "template_id": "string", "similarity_score": 0.85 }
}
```
`best_match` is `null` when no candidate scores ≥ 0.5.

---

### T-05: `decompose-process-steps`

**Source skill removed:** `process-decomposer/SKILL.md`  
**What it does:** Decomposes business goal + entities into an ordered step list with BPMN element hints.  
**Risk level:** L2

**Input:**
```json
{ "goal": "string", "entities": "EntityOutput", "template_hint": "TemplateCandidate (optional)" }
```

**Output:**
```json
{
  "steps": [{
    "id": "s1",
    "name": "string",
    "type": "action|decision|event|subprocess",
    "bpmn_hint": "startEvent|endEvent|userTask|serviceTask|exclusiveGateway|parallelGateway",
    "actor": "string",
    "preconditions": ["string"],
    "description": "string"
  }]
}
```

---

### T-06: `resolve-step-dependencies`

**Source skill removed:** `dependency-resolver/SKILL.md`  
**What it does:** Builds a directed acyclic graph from step.preconditions, annotating loop-back edges.  
**Risk level:** L1

**Input:**
```json
{ "steps": "Step[]" }
```

**Output:**
```json
{
  "dag": {
    "nodes": ["string"],
    "edges": [{ "from": "string", "to": "string", "type": "sequence|conditional|loop_back", "condition": "string (optional)" }]
  }
}
```

---

### T-07: `identify-parallel-steps`

**Source skill removed:** `parallel-optimizer/SKILL.md`  
**What it does:** Traverses the DAG to find steps with no mutual dependencies, groups them as parallelizable.  
**Risk level:** L1

**Input:**
```json
{ "steps": "Step[]", "dag": "DAG" }
```

**Output:**
```json
{
  "parallel_groups": [["s3", "s4"], ["s5", "s6"]],
  "annotated_steps": [{ "id": "string", "parallel_group_id": "string|null" }]
}
```

---

### T-08: `map-steps-to-bpmn-elements`

**Source skill removed:** `bpmn-element-mapper/SKILL.md`  
**What it does:** Maps each step + DAG edge to a BPMN 2.0 element type and assigns BPMN IDs.  
**Risk level:** L2

**Mapping rules:** single out-degree start → startEvent; no successors → endEvent; multi-conditional out-degree → exclusiveGateway; parallel split → parallelGateway; all others → task.

**Input:**
```json
{ "steps": "Step[]", "dag": "DAG" }
```

**Output:**
```json
{
  "element_map": [{
    "step_id": "string",
    "bpmn_type": "startEvent|endEvent|task|exclusiveGateway|parallelGateway|intermediateCatchEvent|intermediateThrowEvent",
    "bpmn_id": "Element_N",
    "name": "string"
  }]
}
```

---

### T-09: `classify-bpmn-task-types`

**Source skill removed:** `bpmn-task-classifier/SKILL.md`  
**What it does:** Determines task subtypes (userTask / serviceTask / scriptTask / manualTask) from actor type and description keywords.  
**Risk level:** L1

**Classification logic:** actor is human role → userTask; actor is external system/API → serviceTask; actor is automated logic → scriptTask; no system actor → manualTask.

**Input:**
```json
{ "element_map": "ElementMapping[]", "steps": "Step[]" }
```

**Output:**
```json
{
  "classified_elements": [{
    "bpmn_id": "string",
    "bpmn_type": "userTask|serviceTask|scriptTask|manualTask|startEvent|endEvent|exclusiveGateway|parallelGateway"
  }]
}
```

---

### T-10: `assemble-bpmn-model`

**Source skill removed:** `bpmn-model-assembler/SKILL.md`  
**What it does:** Combines classified elements, sequence flows, and participant/lane assignments into a ProcessModel object ready for XML serialization.  
**Risk level:** L2

**Input:**
```json
{
  "classified_elements": "ElementMapping[]",
  "participants": "Participant[]",
  "lanes": "Lane[]",
  "message_flows": "MessageFlow[]"
}
```

**Output:**
```json
{
  "process": {
    "id": "string",
    "name": "string",
    "flowNodes": [{ "id": "string", "type": "string", "name": "string" }],
    "sequenceFlows": [{ "id": "string", "sourceRef": "string", "targetRef": "string", "conditionExpression": "string (optional)" }]
  }
}
```

---

### T-11: `assign-bpmn-participants`

**Source skill removed:** `bpmn-participant-organizer/SKILL.md`  
**What it does:** Groups BPMN elements into pools (participants) and lanes based on actor/system assignments from entities.  
**Risk level:** L2

**Input:**
```json
{ "classified_elements": "ElementMapping[]", "entities": "EntityOutput" }
```

**Output:**
```json
{
  "participants": [{ "id": "Participant_N", "name": "string", "processRef": "string" }],
  "lanes": [{ "id": "Lane_N", "name": "string", "participant_id": "string", "flowNodeRefs": ["string"] }],
  "message_flows": [{ "id": "Flow_N", "sourceRef": "string", "targetRef": "string" }]
}
```

---

### T-12: `serialize-bpmn-xml`

**Source skill removed:** `bpmn-xml-serializer/SKILL.md`  
**What it does:** Serializes ProcessModel + participants + lanes + message_flows into a BPMN 2.0 XML string with placeholder BPMNDI layout.  
**Risk level:** L1

**Required namespaces:** `xmlns`, `xmlns:bpmndi`, `xmlns:dc`, `xmlns:di`, `xmlns:bioc`

**Input:**
```json
{
  "process": "ProcessModel",
  "participants": "Participant[]",
  "lanes": "Lane[]",
  "message_flows": "MessageFlow[]"
}
```

**Output:**
```json
{ "bpmn_xml": "string (complete BPMN 2.0 XML)" }
```

---

### T-13: `optimize-bpmn-layout`

**Source skill removed:** `bpmn-diagram-optimizer/SKILL.md`  
**What it does:** Applies three-pass optimization to BPMNDI section: (1) orthogonal layout with 180px H / 100px V spacing, (2) color styling by element type, (3) label deconfliction.  
**Risk level:** L2 (modifies XML coordinates and visual attributes, does NOT modify process logic)

**Color palette:**
- startEvent: `#52B415` stroke / `#E8F5E9` fill
- endEvent: `#E53935` stroke / `#FFEBEE` fill
- userTask: `#1E88E5` stroke / `#E3F2FD` fill
- serviceTask: `#FB8C00` stroke / `#FFF3E0` fill
- gateway: `#FDD835` stroke / `#FFFDE7` fill

**Input:**
```json
{ "bpmn_xml": "string" }
```

**Output:**
```json
{
  "optimized_xml": "string",
  "layout_stats": { "nodes_positioned": 0, "edges_routed": 0, "labels_resolved": 0 }
}
```

---

## Tool Dependency Graph

```
User Description
      │
  T-01 parse-business-intent
      │
  T-02 extract-process-entities
      │
  T-03 detect-description-ambiguity ──► clarification if needed
      │
  T-04 match-bpmn-template
      │
  T-05 decompose-process-steps  ◄─── (skip if template match ≥0.8)
      │
  T-06 resolve-step-dependencies
      │
  T-07 identify-parallel-steps
      │
  T-08 map-steps-to-bpmn-elements
      │
  T-09 classify-bpmn-task-types
      │
  T-11 assign-bpmn-participants ─┐
                                  ├──► T-10 assemble-bpmn-model
                                  │
                              T-12 serialize-bpmn-xml
                                  │
                              T-13 optimize-bpmn-layout
                                  │
                          (BPMN 2.0 XML output)
```
