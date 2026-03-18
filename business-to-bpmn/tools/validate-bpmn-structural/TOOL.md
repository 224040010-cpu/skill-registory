tool_name: validate-bpmn-structural
display_name: Validate BPMN Structural
description: >
  Validates a BPMN 2.0 XML string for structural compliance (namespaces, required
  elements, ID uniqueness, flow references) and logical consistency (orphan nodes,
  dead ends, gateway arity, deadlock patterns). Returns a validation report.

category: validation

risk:
  level: L0
  side_effects: none
  idempotent: true
  requires_approval: false

ownership:
  team: bpmn
  service: bpmn-tools

input_schema:
  type: object
  required:
    - bpmn_xml
  properties:
    bpmn_xml:
      type: string
      description: >
        A BPMN 2.0 compliant XML string. Must begin with the standard XML declaration
        and include a <definitions> root element with required namespaces.
    strict_mode:
      type: boolean
      description: >
        When true, treats LOGIC_006 (missing gateway conditionExpression) as an
        error instead of a warning. Default: false.
      default: false

output_schema:
  type: object
  properties:
    valid:
      type: boolean
      description: >
        True when no errors with severity "error" were found. False if one or
        more errors are present. Warnings alone do not set valid to false.
    structural_checks:
      type: object
      description: Summary counts for structural validation phase.
      properties:
        passed:
          type: integer
          description: Number of structural checks that passed.
        failed:
          type: integer
          description: Number of structural checks that failed.
    logical_checks:
      type: object
      description: Summary counts for logical consistency phase.
      properties:
        passed:
          type: integer
          description: Number of logical checks that passed.
        failed:
          type: integer
          description: Number of logical checks that failed.
    errors:
      type: array
      description: List of validation errors (severity "error") that make valid=false.
      items:
        type: object
        properties:
          code:
            type: string
            description: >
              Error code from the defined set: STRUCT_001-006, LOGIC_001-006.
          severity:
            type: string
            enum: [error, warning]
            description: Severity level.
          message:
            type: string
            description: Human-readable description of the error.
          element_id:
            type: string
            description: The BPMN element ID where the error was found (if applicable).
    warnings:
      type: array
      description: >
        Non-blocking issues that do not affect valid=true. Same structure as errors.
      items:
        type: object
        properties:
          code:
            type: string
          severity:
            type: string
          message:
            type: string
          element_id:
            type: string

errors:
  - code: INVALID_XML
    message: >
      The input is not valid XML. Check that the string is well-formed before
      calling this tool.
    retryable: false

  - code: NOT_BPMN_XML
    message: >
      The XML does not contain a <definitions> root element or the required
      BPMN 2.0 namespace. Ensure the input is BPMN 2.0 XML, not plain XML.
    retryable: false

  - code: EXECUTION_FAILED
    message: >
      Tool execution failed due to an internal error during XML parsing or
      graph traversal. Retry once; if the error persists, report to the bpmn team.
    retryable: true

usage:
  when_to_use:
    - >
      After serialize-bpmn-xml generates a BPMN XML string, before delivering
      to the user — to catch serialization errors early in the pipeline.
    - >
      When a user provides an existing .bpmn file and asks if it is valid
      for use in bpmn.io or Camunda.
    - >
      As the first phase of the validating-bpmn-compliance skill before
      evaluating intent coverage.

  when_not_to_use:
    - >
      Do not use to validate non-BPMN XML (e.g., plain XML, SVG, HTML).
      Use a general XML schema validator instead.
    - >
      Do not call before serialize-bpmn-xml — there is no XML to validate
      until serialization is complete.

  called_by_skills:
    - converting-business-to-bpmn
    - validating-bpmn-compliance

implementation:
  type: mcp
  endpoint: bpmn-tools:validate_bpmn_structural
  timeout_ms: 3000
  notes: >
    Implemented as a pure in-memory XML parser + graph traversal.
    No external service calls. Uses Python xml.etree.ElementTree for parsing
    and a BFS algorithm for reachability checks. L0 risk: no I/O, fully deterministic.
    The 12 checks map to codes STRUCT_001-006 and LOGIC_001-006.
