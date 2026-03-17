tool_name: parse-business-intent
display_name: Parse Business Intent
description: >
  Parses a natural language business description into a structured intent object
  containing business_type, goal, constraints, and scope fields.

category: parsing

risk:
  level: L1
  side_effects: read
  idempotent: true
  requires_approval: false

ownership:
  team: bpmn
  service: bpmn-tools

input_schema:
  type: object
  required:
    - user_description
  properties:
    user_description:
      type: string
      description: >
        The user's natural language description of a business process or scenario.
        Minimum 10 characters. Can be in Chinese or English.

output_schema:
  type: object
  properties:
    business_type:
      type: string
      description: >
        Detected business process category. One of: approval, alert-handling,
        data-sync, order-processing, reporting, onboarding, ticket-routing, other.
      enum:
        - approval
        - alert-handling
        - data-sync
        - order-processing
        - reporting
        - onboarding
        - ticket-routing
        - other
    goal:
      type: string
      description: >
        The primary objective the process should achieve, expressed as
        a verb phrase (e.g. "自动诊断充电桩告警并分级恢复").
    constraints:
      type: array
      items:
        type: string
      description: >
        List of explicit or strongly implied constraints from the description
        (e.g. time limits, approval tiers, retry policies, role restrictions).
    scope:
      type: string
      description: >
        The boundary of the process — systems, departments, or devices involved
        (e.g. "设备端 + 云端Agent").

errors:
  - code: INVALID_INPUT
    message: >
      user_description is missing, empty, or shorter than 10 characters.
      Provide a meaningful business process description.
    retryable: false

  - code: PARSE_FAILED
    message: >
      Failed to extract structured intent from the description. The description
      may be too abstract or unrelated to a business process.
    retryable: true

  - code: SERVICE_UNAVAILABLE
    message: >
      The LLM inference service is temporarily unavailable. Retry after a short delay.
    retryable: true

usage:
  when_to_use:
    - >
      As the first step in any business-to-BPMN pipeline, before entity extraction
      or template matching — intent must be structured before downstream tools can run.
    - >
      When a skill receives a free-form user description and needs to determine
      the business_type for routing or template selection.

  when_not_to_use:
    - >
      Do not call when the intent is already structured (skip to extract-process-entities).
    - >
      Do not use for non-business inputs (technical documentation, code descriptions,
      personal requests) — the output will be unreliable.

  called_by_skills:
    - converting-business-to-bpmn
    - decomposing-business-process

implementation:
  type: mcp
  endpoint: bpmn-tools:parse_business_intent
  timeout_ms: 8000
  notes: >
    Implemented as an LLM inference call with a structured output prompt.
    The model is instructed to extract exactly four fields and return valid JSON.
    If business_type cannot be reliably determined, defaults to "other".
    Does not call any external database — reads only from the input string.
