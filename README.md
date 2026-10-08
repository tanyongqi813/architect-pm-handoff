# Architect PM Handoff

A Codex-only skill for using Codex as the architecture, planning, and review role while another coding agent performs implementation.

## What it does

- Inspects the repository before proposing changes.
- Converts requirements into ordered, micro-batched Task Specs.
- Keeps architecture and task documents as the source of truth.
- Reviews diffs, errors, test results, and implementation reports.
- Returns explicit review verdicts and advances the next ready task.

## Host boundary

This workflow is intended for OpenAI Codex. Cursor should use its own project or user Rules and must not execute this skill.

## Install on another device

Install the skill directory from this repository into your Codex user skills directory:

```text
~/.codex/skills/architect-pm-handoff/
```

The installed directory must contain both `SKILL.md` and `agents/openai.yaml`. Restart Codex and start a new task after installation.

You can then invoke it explicitly:

```text
Use $architect-pm-handoff to plan this requirement into executable Task Specs.
```

The repository also includes portable and Codex compatibility plugin manifests for plugin-based installation.

## Expected project files

The workflow uses these files when present:

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/TASK_LIST.md
docs/tasks/TASK-xxx.md
docs/decisions/ADR-xxx.md
```

## License

MIT
