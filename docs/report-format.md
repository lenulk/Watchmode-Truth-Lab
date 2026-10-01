# CLI and report contract

The default console output is UTF-8 JSON. `--format summary` changes only console presentation; `--report` always saves JSON. Errors from invalid input/export use stderr and exit 2. `--validate`, `--doctor` and `--init` have their own action result objects; freshness report consumers should inspect the action/status rather than assuming all JSON has `attempts`.

## Freshness report schema 1

| Field | Meaning |
| --- | --- |
| `schema_version` | 1; readers should tolerate additive fields and reject unknown incompatible versions |
| `status` | Overall pass/stale/timeout/inconclusive |
| `started_at_utc` | UTC start timestamp |
| `config`, `config_sha256` | Scenario filename and exact input-file hash |
| `command`, `mutation_command`, `tool_version` | Scenario command inputs and captured watched-tool version |
| `environment`, `oracle` | Observed runtime/storage details and applied oracle policy |
| `startup` | Baseline readiness result; startup failure makes the run inconclusive |
| `attempts` | Per-round mutation, expected/observed hashes, status/reason, sample and latency details |
| `failure_rate` | Failed observed rounds / attempted rounds; null if none ran |
| `pass_latency` | Median/p95 for passed rounds; null if none passed |
| `logs` | Bounded watched-command logs, including browser metric records when applicable |
| `reproduction` | Scenario filename, round count, mutation and invocation; requires original scenario/dependencies/environment |

Record `--version` with artifacts used for reproduction. This report is diagnostic evidence, not a standalone archive of dependencies or arbitrary configuration secrets. The original scenario matching `config_sha256` is required. Capture the artifact checksum to identify installed code.

`reproduction.argv` preserves literal arguments and the current interpreter for subprocess execution without a shell. `reproduction.cli` quotes those arguments for `cli_shell` (`powershell` on Windows, `posix` elsewhere). Run from the scenario directory; keep the original environment/dependencies. These additive schema 1 fields avoid interpreting spaces, apostrophes or dollar signs in a filename. A quoted invocation alone does not preserve arbitrary environment variables.

## Decision semantics

- `pass`: matching observations met the configured stable-window policy before the deadline while the watched process was alive.
- `stale`: readable output failed to reach a stable matching value by the deadline; inspect `reason` and observed hash.
- `timeout`: output was unavailable, or matching samples could not complete the observation policy before the deadline. A late match is never accepted.
- `inconclusive`: startup was not ready, the process exited, extraction/body policy prevented a conclusion or a mutation failed/timed out.

An internal mutation I/O failure records `reason: mutation_failed` and `mutation_error` containing the exception `type`, numeric `errno` and `winerror` (null when unavailable). Exception text and filesystem paths are not included in this field. The run stops after that attempt, still exports its completed report and returns exit 1. External mutation failures retain `mutation_command_failed` and their separate command result.

On Windows, atomic replacement retries WinError 5/32 for at most one second in short interruptible sleeps. The staged content is written once; unrelated errors propagate immediately into the inconclusive result. A permanent replacement denial preserves the old target and removes the staging file. This retry budget precedes observation latency and does not extend the configured observation deadline.

Pending HTTP slices are not new observations. They cannot themselves pass a round. A pending request is retained within the overall budget and canceled at the observation boundary. Actual sampled matches establish the configured policy, not correctness between samples or indefinitely afterward.

Overall precedence is startup failure/inconclusive, then a round inconclusive, stale, timeout, otherwise pass. Ordinary process teardown happens after the observations; teardown-time child log messages should be read in that order rather than replacing the recorded decision.

Latency starts after mutation returns; external mutator duration is separate. Comparisons across hardware/storage loads are not controlled performance benchmarks. Hashes refer to extracted token bytes when using a regex; raw output hashes are available on applicable failures.

## Browser metric records

`WTL_BROWSER_STATE` logs contain token, independent document session, optional retained state and update metric. The generic adapter labels observed DOM changes separately from application-supplied HMR callback counts. Session continuity and retained state are verified by the adapter; matrix acceptance also checks them. Playwright WebKit reports describe that engine/build, not Safari.

## Compatibility and interruption

Existing `watchmode-truth-lab scenario.json --rounds ... --mutation ... --report ...` invocation and default JSON are retained. Exit codes 0/1/2 are retained; new diagnostics use 2 when not ready. Controlled cancellation returns 130 with stderr notice and no completed report. A stale previous report must not be mistaken for a canceled run's output.

Reports are staged in the destination directory, flushed and replaced after completion. Active partial-write/replace faults are tested to preserve prior bytes. This is not a guarantee of durability after every possible power/storage failure. Deliberately detached/cross-OS processes remain outside ordinary-descendant containment.
