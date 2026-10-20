# Architect PM Handoff

A role-based workflow for a lead AI to plan repository changes, hand bounded work to downstream agents, and review results without coupling long-term planning to execution context.

[中文说明](skills/architect-pm-handoff/README.zh-CN.md)

## What it does

- Keeps durable planning facts in Task Specs.
- Generates a short, per-attempt Execution Capsule with source anchors, a file allowlist, modification limit, targeted verification, known baselines, stop conditions, and a fixed report format.
- Stores each verdict and finding set in a separate Review Record.
- Produces delta capsules for unresolved findings instead of redispatching the complete original Task.
- Assigns mandatory `P0`–`P3` priority and `Low`/`Medium`/`High` difficulty.
- Treats an absent executor-handoff heading as `no dispatch`.
- Supports legacy Task-Spec-only projects without fabricating missing execution facts.
- Can optionally commit and push approved Task-scoped changes with traceable metadata.

## Role boundary

The workflow is selected by role, not vendor. Claude, Codex, or another capable agent may act as lead when assigned architecture, planning, review, and acceptance authority. Any suitable downstream agent may implement an Execution Capsule. Shared Task Specs, Capsules, and Review Records remain vendor-neutral; CLI flags, recovery behavior, authentication, and model options belong in channel adapters.

## Install

Install `skills/architect-pm-handoff/` into the user skill directory supported by the lead-AI host. For Codex, use:

```text
~/.codex/skills/architect-pm-handoff/
```

The directory must include `SKILL.md` and its `references/`, `scripts/`, and host metadata where applicable. Restart the host or start a new conversation after installation.

## Project artifacts

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/TASK_LIST.md
docs/tasks/TASK-XXX.md
docs/execution/TASK-XXX/attempt-NN.md
docs/reviews/TASK-XXX/attempt-NN.md
docs/decisions/ADR-XXX.md
```

Templates:

- [Task Spec](skills/architect-pm-handoff/references/task-spec.md)
- [Execution Capsule](skills/architect-pm-handoff/references/executor-handoff.md)
- [Review Record](skills/architect-pm-handoff/references/review-record.md)

## Validation

Run the skill package validator and artifact tests after changes:

```text
python3 <skill-creator>/scripts/quick_validate.py skills/architect-pm-handoff
python3 -m unittest discover -s skills/architect-pm-handoff/tests -p 'test_*.py'
```

Projects can validate a planning, dispatch, review, or legacy artifact set with `scripts/validate_handoff_artifacts.py`.

## Optional approved-task Git sync

Automatic commit and push are disabled by default. Copy `config.example.toml` to the private, ignored `config.local.toml` and enable the desired values. The sync helper stages only explicit Task paths, requires an existing upstream before pushing, records review metadata, and never force-pushes or rewrites history.

## License

MIT
