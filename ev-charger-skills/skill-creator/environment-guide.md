# Skill Creator - Environment-Specific Guide

## Claude.ai

In Claude.ai, the core workflow is the same but no subagents means some mechanics change:

**Running test cases**: No parallel execution. For each test case, read the skill's SKILL.md, then follow its instructions yourself. Do them one at a time. Skip baseline runs.

**Reviewing results**: If you can't open a browser, present results directly in conversation. For each test case, show prompt and output. If output is a file, save it and tell user where to download.

**Benchmarking**: Skip quantitative benchmarking - focus on qualitative feedback.

**The iteration loop**: Same as before, just without browser reviewer.

**Description optimization**: Requires `claude` CLI tool - skip on Claude.ai.

**Blind comparison**: Requires subagents - skip.

**Packaging**: Works anywhere with Python and filesystem.

## Cowork

Main things to know:

- You have subagents, so main workflow works
- If severe timeout problems, run test prompts in series
- No browser/display - use `--static <output_path>` for viewer
- Proffer link for user to open HTML in browser
- Feedback works via downloaded `feedback.json`
- Packaging works
- Description optimization works (uses `claude -p` via subprocess)

**IMPORTANT**: Always generate eval viewer BEFORE evaluating yourself. Get results in front of human ASAP!

## Claude Code

Full functionality available:
- Subagents for parallel test execution
- Browser for eval viewer
- CLI tools for description optimization
- All scripts work

## Directory Structure

```
<skill-name>-workspace/
├── iteration-1/
│   ├── eval-0-descriptive-name/
│   │   ├── with_skill/
│   │   │   ├── outputs/
│   │   │   └── timing.json
│   │   ├── without_skill/
│   │   │   ├── outputs/
│   │   │   └── timing.json
│   │   ├── eval_metadata.json
│   │   └── grading.json
│   ├── benchmark.json
│   └── benchmark.md
├── iteration-2/
│   └── ...
└── skill-snapshot/  # For baseline when improving existing skill
```
