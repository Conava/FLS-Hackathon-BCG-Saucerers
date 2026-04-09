# CLAUDE.md

This file is the single source of non-obvious project context — things that cannot be figured out from the code, tests, or git history alone. Do not add anything here that is already discoverable or obvious.

## Workflow Orchestration

### Pipeline First
- Use `/devline` for any non-trivial task (3+ steps or architectural decisions). It handles brainstorming, planning, parallel implementation, review, and documentation.
- Use `/devline:implement` only for small, well-scoped tasks where the plan is obvious.
- If something goes sideways during implementation, stop and re-plan — do not patch forward.

### Subagent Strategy
- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex problems, throw more compute at it via subagents — one task per subagent for focused execution.

## Core Principles

- **Simplicity First**: Make every change as simple as possible.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Demand Elegance**: For non-trivial changes, pause and ask "is there a more elegant way?" If a fix feels hacky, implement the elegant solution. Skip this for simple, obvious fixes — don't over-engineer.
- **Minimize Output Noise**: When running commands that may produce large output (test suites, logs, builds), proactively use `| grep`, `| head`, or flags like `--quiet`/`--failed-only` to filter results. Only run unfiltered if filtered output is insufficient.

## Learning & Recovery

This project uses a self-correcting pipeline. Agents (implementer, reviewer, deep-review) continuously challenge themselves: "Is this a one-off issue or a broader pattern?" When they identify a non-obvious codebase pattern, they report it as a lesson and the orchestrator appends it to the Lessons and Memory section below.

**For the pipeline (automatic):** Agents extract lessons during normal work. No approval needed — the agent already analyzed the issue. Lessons are shown in the pipeline completion summary.

**For direct conversations (manual):** When the user corrects you or you discover a non-obvious pattern outside the pipeline:
1. Identify the root cause — not just the symptom.
2. Assess scope — one-off or pattern?
3. If it's a pattern, formulate as: pattern (what triggers it), reason (why it happens), solution (how to prevent it).
4. Append it to the Lessons and Memory section below.

**Always:** Review existing lessons before starting work. If a lesson covers the situation, follow it. Update stale lessons rather than adding duplicates.

## Project Context

<!-- Add non-obvious context here. Examples: -->
<!-- - Build/test/lint commands if non-standard -->
<!-- - Naming conventions not enforceable by linters -->
<!-- - Architectural decisions that differ from common patterns -->
<!-- - Required environment variables or local services -->
<!-- - Common gotchas specific to this codebase -->

## Lessons and Memory

<!-- Lessons are added here automatically via the Learning & Recovery process above. -->
<!-- Format: **Pattern**: ... | **Reason**: ... | **Solution**: ... -->
