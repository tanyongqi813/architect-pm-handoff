# Kimi channel adapter boundary

Use this reference only when dispatching through a Kimi execution channel. Read `channel-budgeting.md` first.

- Put model selection, account/quota checks, session identifiers, continuation flags, and default time/call budgets in the adapter's private configuration.
- Query quota only through capabilities actually exposed by the installed client or service. If no authoritative quota API exists, report quota as unknown; do not estimate it from prompt history.
- Prefer a fresh session for a new Capsule. Continue an existing session only for the adapter's one allowed correction and only when bounded history can be maintained.
- If the channel reports exhaustion or stops responding, preserve the workspace and request the fixed `partial + checkpoint` report when possible. Do not loop, switch models automatically, or resend the complete task.
- The adapter cannot make a prompt-level time/call budget into a hard stop. Mark a limit `runner_enforced` only when the runner itself implements and reports it.

No Kimi-specific field belongs in shared Task Specs, Capsules, or Review Records.
