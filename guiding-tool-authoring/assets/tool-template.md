# TOOL.md Template
# Copy this file to <your-tool-name>/TOOL.md and fill in every field.
# Fields marked [REQUIRED] must be completed before submission.
# Fields marked [OPTIONAL] can be left empty but improve discoverability.
#
# Run: python guiding-tool-authoring/scripts/validate_tool.py <path/to/TOOL.md>
# Target score: ≥ 40/50 to register, ≥ 45/50 to approve without changes.

tool_name: replace-with-kebab-case-name          # [REQUIRED] e.g. parse-business-intent
display_name: Replace With Human Readable Name   # [REQUIRED]
description: >                                   # [REQUIRED] ≤120 chars, third-person, specific
  One-sentence description of what this tool does and what it returns.
  No vague verbs (handles, processes, deals with). Example:
  "Parses a natural language business description into a structured intent object
  containing business_type, goal, constraints, and scope."

category: parsing                                # [REQUIRED] parsing | transformation | validation | execution | retrieval | computation

risk:
  level: L1                                      # [REQUIRED] L0 | L1 | L2 | L3 | L4
  side_effects: read                             # [REQUIRED] none | read | write | external
  idempotent: true                               # [REQUIRED] true | false
  requires_approval: false                       # [REQUIRED for L3/L4] true | false

ownership:
  team: replace-with-team-name                   # [REQUIRED]
  service: replace-with-mcp-server-name          # [REQUIRED] the MCP server this tool belongs to

input_schema:
  type: object
  required:
    - param_one                                  # [REQUIRED] list all required params
  properties:
    param_one:
      type: string                               # [REQUIRED] string | number | boolean | object | array
      description: >                             # [REQUIRED] what this param means
        Description of param_one.
    param_two:
      type: string
      description: Description of param_two (optional parameter).
      enum:                                      # [OPTIONAL] list valid values if fixed set
        - value_a
        - value_b
      default: value_a                           # [OPTIONAL]

output_schema:
  type: object
  properties:
    field_one:
      type: string                               # [REQUIRED] type for every output field
      description: Description of field_one.    # [REQUIRED] description for every output field
    field_two:
      type: array
      items:
        type: object
        properties:
          sub_field:
            type: string
            description: Description of sub_field.
      description: List of items returned.

errors:
  - code: INVALID_INPUT                          # [REQUIRED] UPPER_SNAKE_CASE
    message: >                                   # [REQUIRED] human-readable description
      Input parameter X is missing or has an invalid value.
    retryable: false                             # [REQUIRED] false = fix input before retry

  - code: EXECUTION_FAILED                       # [REQUIRED] at least one system-level error
    message: >
      Tool execution failed due to an internal error. Check logs for details.
    retryable: true                              # [REQUIRED] true = safe to retry automatically

  # Add more error codes as needed:
  # - code: TIMEOUT
  #   message: Tool timed out after 30 seconds.
  #   retryable: true

usage:
  when_to_use:                                   # [REQUIRED] 2-3 specific scenarios
    - >
      When a skill needs to convert X into structured form before further processing.
    - >
      As the first step in a pipeline that requires typed data.

  when_not_to_use:                               # [REQUIRED] 1-2 anti-patterns
    - >
      Do not use when the input is already structured — unnecessary parsing adds latency.
    - >
      Do not use for multi-step transformation — use the appropriate transformation tool.

  called_by_skills:                              # [OPTIONAL] known skill_names that call this tool
    - skill-name-here

implementation:
  type: mcp                                      # [REQUIRED] mcp | http | internal
  endpoint: mcp-server-name:tool_function_name   # [REQUIRED] fully-qualified MCP call or HTTP endpoint
  timeout_ms: 5000                               # [OPTIONAL] expected timeout
  notes: >                                       # [OPTIONAL] implementation hints for engineers
    Implementation notes for the backend team.
