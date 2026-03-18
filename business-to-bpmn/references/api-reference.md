# API Reference — business-to-bpmn

## Layer 1: 理解层

### intent-parser
- **Input**: `{ user_description: string }`
- **Output**: `{ business_type: string, goal: string, constraints: string[], scope: string }`

### entity-extractor
- **Input**: `{ user_description: string, intent: IntentOutput }`
- **Output**: `{ roles: Entity[], systems: Entity[], data_objects: Entity[], triggers: Entity[] }`

### ambiguity-detector
- **Input**: `{ intent: IntentOutput, entities: EntityOutput }`
- **Output**: `{ has_ambiguity: boolean, ambiguity_points: AmbiguityPoint[], clarification_questions: string[] }`

## Layer 2: 规划层

### bpmn-template-matcher
- **Input**: `{ intent: IntentOutput }`
- **Output**: `{ candidates: TemplateCandidate[], best_match: { template_id: string, similarity_score: number } | null }`

### process-decomposer
- **Input**: `{ goal: string, entities: EntityOutput }`
- **Output**: `{ steps: Step[] }` where Step = `{ id, name, type, bpmn_hint, preconditions, description }`

### dependency-resolver
- **Input**: `{ steps: Step[] }`
- **Output**: `{ dag: { nodes: string[], edges: { from: string, to: string, condition?: string }[] } }`

### parallel-optimizer
- **Input**: `{ dag: DAG }`
- **Output**: `{ execution_plan: { parallel_groups: string[][], sequential_order: string[] } }`

## Layer 3: BPMN 建模层

### bpmn-element-mapper
- **Input**: `{ steps: Step[], dag: DAG }`
- **Output**: `{ element_map: ElementMapping[] }` where ElementMapping = `{ step_id, bpmn_type: "startEvent"|"endEvent"|"task"|"exclusiveGateway"|"parallelGateway"|"intermediateEvent", name }`

### bpmn-task-classifier
- **Input**: `{ element_map: ElementMapping[], entities: EntityOutput }`
- **Output**: `{ task_types: { step_id: string, task_kind: "userTask"|"serviceTask"|"scriptTask" }[] }`

### bpmn-model-assembler
- **Input**: `{ element_map: ElementMapping[], task_types: TaskType[], dag: DAG }`
- **Output**: `{ process: { id, name, flowNodes: FlowNode[], sequenceFlows: SequenceFlow[] } }`

### bpmn-participant-organizer
- **Input**: `{ process: ProcessModel, entities: EntityOutput }`
- **Output**: `{ participants: Participant[], lanes: Lane[], message_flows: MessageFlow[] }`

## Layer 4: BPMN 渲染层

### bpmn-xml-serializer
- **Input**: `{ process: ProcessModel, participants: Participant[], lanes: Lane[], message_flows: MessageFlow[] }`
- **Output**: `{ bpmn_xml: string }`

### bpmn-diagram-optimizer
- **Input**: `{ bpmn_xml: string }`
- **Output**: `{ optimized_xml: string, layout_stats: { nodes_positioned, edges_routed, labels_resolved } }`

## Layer 5: 验证层

### bpmn-compliance-validator
- **Input**: `{ bpmn_xml: string }`
- **Output**: `{ valid: boolean, errors: ValidationError[], warnings: ValidationWarning[] }`

### intent-coverage-evaluator
- **Input**: `{ bpmn_xml: string, original_intent: IntentOutput, original_entities: EntityOutput }`
- **Output**: `{ coverage_score: number, covered_items: string[], missing_items: string[] }`
