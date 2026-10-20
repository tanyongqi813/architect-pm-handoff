# Cursor CLI adapter

Read this reference only after an actionable Execution Capsule exists and the user explicitly authorizes dispatch of that specific attempt through Cursor CLI.

## Adapter boundary

The adapter transports a vendor-neutral capsule. It must not rewrite planning facts, widen scope, select another Task, or add model-specific text to shared repository artifacts.

## Preconditions

- Resolve the repository absolute path and capsule path; confirm Task ID, attempt, priority, difficulty, allowlist, and targeted verification.
- Confirm `agent` or `cursor-agent` is installed and authenticated.
- Authorization is per dispatch. Skill enablement is not standing authorization.
- Do not use GUI automation or GUI fallback.

## Dispatch

Prefer `python3 scripts/dispatch_cursor_cli.py --repo <absolute-path> --capsule docs/execution/TASK-XXX/attempt-NN.md`.

The compact prompt tells the executor to read only the capsule and listed anchors, modify only allowlisted files, run only targeted verification, and return the capsule's Implementation Report. Start a fresh non-interactive session; do not use resume/continue unless explicitly requested.

`--task docs/tasks/TASK-XXX.md` remains a legacy fallback for projects without capsules. It does not provide capsule-level context guarantees and must not be used to fabricate missing execution facts.

## Bounded stall recovery

The default idle threshold is 12 minutes without a stream event. Add `--allow-recovery` only when the user authorizes automatic recovery for this dispatch.

- On the first confirmed stall, terminate the CLI process, preserve its temporary log, restart macOS `Developer: Restart Extension Host` through `scripts/restart_cursor_extension_host.sh`, and run one read-only health probe.
- If the attempt changed the worktree, recover but do not retry; preserve changes for review.
- If the worktree is unchanged and the probe passes, retry once in a fresh session.
- If recovery or retry fails/stalls, stop. Never loop, force recovery, or switch to GUI.

Recovery requires macOS, a running Cursor app, Accessibility permission, and current-dispatch authorization.

## Completion

Capture the concise Implementation Report for architect review. CLI exit zero is not a review verdict. Do not send follow-ups, start parallel executors, or dispatch another capsule automatically.
