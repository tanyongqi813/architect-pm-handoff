# Cursor CLI adapter

Read this reference only after an actionable Execution Capsule exists and the user explicitly authorizes dispatch of that specific attempt through Cursor CLI.

## Adapter boundary

The adapter transports a vendor-neutral capsule. It must not rewrite planning facts, widen scope, select another Task, or add model-specific text to shared repository artifacts.

## Preconditions

- Resolve the repository absolute path and capsule path; confirm Task ID, attempt, priority, difficulty, allowlist, and targeted verification.
- Confirm `agent` or `cursor-agent` is installed and authenticated.
- Authorization is per dispatch. Skill enablement is not standing authorization.
- Normal dispatch must not use GUI automation or GUI fallback.

## Dispatch

Prefer `python3 scripts/dispatch_cursor_cli.py --repo <absolute-path> --capsule docs/execution/TASK-XXX/attempt-NN.md`.

The compact prompt tells the executor to read only the capsule and listed anchors, modify only allowlisted files, run only targeted verification, and return the capsule's Implementation Report. Start a fresh non-interactive session; do not use resume/continue unless explicitly requested.

`--task docs/tasks/TASK-XXX.md` remains a legacy fallback for projects without capsules. It does not provide capsule-level context guarantees and must not be used to fabricate missing execution facts.

Apply the shared rules in `channel-budgeting.md`: one initial execution plus at most one correction by default. Cursor model choice, session continuation, quota observations, and actual timeout enforcement belong to this adapter or its private configuration. Capsule time/call budgets remain soft unless the runner enforces and reports the referenced limit.

## Bounded stall recovery

The default idle threshold is 12 minutes without a stream event. A single macOS GUI action to restart the Extension Host is the only GUI exception, and is allowed only when the user explicitly passes `--allow-recovery` for this specific dispatch.

- On the first confirmed stall, terminate the CLI process, preserve its temporary log, restart macOS `Developer: Restart Extension Host` through `scripts/restart_cursor_extension_host.sh`, and run one read-only health probe.
- If the attempt changed the worktree, recover but do not retry; preserve changes for review.
- If the worktree is unchanged and the probe passes, retry once in a fresh session.
- If recovery or retry fails/stalls, stop. Never loop, force recovery, or switch to GUI.

Recovery restores the execution environment; it is not an alternative dispatch channel and does not broaden file, command, model, or permission authorization. If the stalled attempt changed the worktree, perform at most the one authorized environment recovery and do not retry automatically.

Recovery requires macOS, a running Cursor app, Accessibility permission, and current-dispatch authorization.

## Completion

Capture the concise Implementation Report for architect review. On budget or quota stop, preserve the workspace and capture `partial + checkpoint`, including branch, files, completed scope, remaining gaps, and whether verification covers the latest code. CLI exit zero is not a review verdict. Do not send more than one bounded correction, start parallel executors, or dispatch another capsule automatically.
