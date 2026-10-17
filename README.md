# Architect PM Handoff

A Codex-only skill for using Codex as the architecture, planning, and review role while another coding agent performs implementation.

## What it does

- Inspects the repository before proposing changes.
- Converts requirements into ordered, micro-batched Task Specs.
- Assigns mandatory `P0`–`P3` priority and `Low`/`Medium`/`High` difficulty to every Task.
- Keeps architecture and task documents as the source of truth.
- Reviews diffs, errors, test results, and implementation reports.
- Reassesses unfinished-task priorities after every review, returns an explicit verdict, and advances the highest-priority unblocked task.
- Emits the executor-handoff heading only when exactly one complete, unlocked Task or concrete correction is actionable; downstream automation must treat an absent heading as `no dispatch`.
- Can optionally commit and push approved Task-scoped changes with traceable commit metadata while rejecting unrelated staged files.

## Host boundary

This workflow is intended for OpenAI Codex. Implementation agents should use their own project or user rules and must not execute this skill.

Task Specs remain vendor-neutral: they record difficulty rather than naming a specific model, product, or coding agent. Each user or team can map difficulty levels to its own executors. The included Cursor CLI dispatcher is an optional local adapter and does not change the shared document format.

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

## Optional approved-task Git sync

Automatic commit and push are disabled by default. Copy `config.example.toml` to `config.local.toml` inside the installed Skill directory and enable the desired values. Keep `config.local.toml` private; it is ignored by this repository.

The sync workflow stages only explicit Task paths, requires an existing branch upstream before pushing, records the Task ID, review verdict, priority, difficulty, verification, and changed paths in the commit message, and never force-pushes or rewrites history.

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
