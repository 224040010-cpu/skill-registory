# Repository boundaries

## Role

This repository is the capability control plane. It decides which Skills and Tools exist, which versions are approved, their risk and ownership, and which descriptors may be published to consumers.

## Owned here

- Skill and Tool source specifications.
- Capability planning and authoring guidance.
- Admission, state and governance checks.
- Registry lifecycle and risk policy.
- Versioned `catalog/catalog.snapshot.json` publication.
- The canonical copy of `contracts/system-definition.json`.

## Owned by `agent-workflow-factory`

- Business-language contracts and BPMN generation.
- BPMN parsing and Workflow IR compilation.
- Graph routing, Loop specifications and Agent Profile compilation.
- Runtime adapters, sessions, scheduling, trajectory, resume and replay.

## Integration contract

1. This repository publishes a catalog containing only `approved` and `restricted` assets.
2. The workflow factory resolves required names against one immutable snapshot.
3. It writes versions and digests to `registry.lock.json` before packaging.
4. Runtime execution uses the lock and never reads the Registry main branch.
5. Runtime evidence returns as a governance recommendation; it cannot mutate lifecycle state.

## Shared definition changes

`contracts/system-definition.json` is logically single-source and physically mirrored into both repositories. A change must:

1. update the canonical file here;
2. increment `definition_version`;
3. refresh `system-definition.sha256`;
4. synchronize the workflow-factory mirror;
5. pass byte-for-byte verification in both repositories.

Use `scripts/verify_system_definition.py --peer <peer-definition>` when both repositories are checked out together.
