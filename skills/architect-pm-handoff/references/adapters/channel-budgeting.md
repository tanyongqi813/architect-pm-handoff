# Channel budget and continuation adapter contract

Read this reference when implementing or evaluating a dispatch adapter.

The shared Capsule states a vendor-neutral acceptance slice and budget semantics. The adapter owns channel-specific quota checks, model selection, session creation or continuation, and any actual runtime limits.

## Required behavior

- Distinguish a prompt-only soft budget from a runner-enforced timeout/call limit. Never imply that prompt text can terminate a process.
- Treat quota displays and estimates as advisory unless the channel exposes an authoritative API. Never promise exact remaining quota prediction.
- Default automation to one initial execution plus at most one correction. After that, stop and return the current diff/checkpoint to the lead.
- Never resend the full original Task Spec or Capsule as a correction. A continuation receives only the current capsule plus the checkpoint facts needed by that adapter.
- On quota exhaustion, context exhaustion, timeout, or voluntary budget stop, preserve the workspace and require a `partial + checkpoint` report.
- Resume a session only when the channel supports it and doing so does not rehydrate unbounded history. Otherwise start a fresh session from the new incremental capsule.
- Model choice and default budgets stay in adapter/private configuration, not Task Specs, Capsules, or Review Records.

The lead must inspect the actual workspace diff before accepting a checkpoint or producing a new `checkpoint_resume` capsule. Executor summaries are evidence pointers, not acceptance proof.
