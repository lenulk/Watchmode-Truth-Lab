# Watchmode Truth Lab

An experimental, black-box CLI that checks whether a watch process produces the latest **observable bytes** after a source file changes. It does not count filesystem events or infer their cause.

## Try it

Requires Python 3.10 or newer. From this directory:

```sh
python -m watchmode_truth_lab example.json --rounds 3 --mutation atomic_replace --report reports/example.json
python scripts/test_cycle.py --label local-regression --purpose "Verify local integrations"
```

`example.json` starts a tiny polling generator in a copied temporary fixture. The CLI waits for its baseline output, mutates `input.txt`, and waits for exact output bytes to match the final mutation for a short stable window. Exit code 0 means all rounds passed; 1 means a freshness check failed or was inconclusive; 2 means CLI input was invalid. The JSON includes hashes, latency to the first stable match, sample counts, environment, logs, and a reproduction command/config. Scenario metadata uses a filename and SHA-256 instead of an absolute config path. Child-process logs may still contain local paths or other sensitive data, so review reports before publishing. Run reproduction commands from the directory containing the scenario.

## Test, record, analyze, improve

Every automated test cycle saves JSON outcomes and a console log under `evidence/test-runs/`, including failures and skips. Append its analysis, repair, verification, and remaining limits to [the test log](docs/test-log.md) before the next cycle. Keep failed evidence when a repair passes. The current [results](docs/current-results.md) link to complete experimental matrices.

```sh
python scripts/test_cycle.py --label oracle-regression --purpose "Check deadline and process-exit decisions" --test test_oracle
python scripts/scenario_cycle.py --label "Local Vite" --output evidence/matrices/local-run-001 --rounds 20
```

Matrix scripts require a new output directory so previous evidence cannot be overwritten. A clean run establishes the tested cases, not absence of every possible bug.

## Run against Vite

Install the pinned Vite 8.3.1 dependency with `pnpm install --frozen-lockfile` and ensure Node.js is on `PATH`. Then run from this directory:

```sh
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation overwrite --report reports/vite-native-overwrite.json
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation atomic_replace --report reports/vite-native-atomic.json
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation burst --report reports/vite-native-burst.json
python -m watchmode_truth_lab vite.polling.json --rounds 20 --mutation overwrite --report reports/vite-polling-overwrite.json
```

The fixture serves `/src/token.js` through Vite. The oracle extracts the exported token from the transformed HTTP response. This exercises Vite's server-side module invalidation after a watched change. It does not verify browser HMR state. The polling scenario is a control for the documented watcher option. Reports are ignored by Git by default; save the ones used as evidence separately.

### Browser HMR

The separate browser adapter uses pinned Playwright Core with an existing installed Chrome. It reads the actual DOM, records HMR callback counts, and rejects a changed page session. It launches an isolated headless browser profile. `WTL_BROWSER_CHANNEL=msedge` may select installed Edge; only Windows Chrome is currently verified.

```sh
python -m watchmode_truth_lab vite.browser.json --rounds 3 --mutation atomic_replace --report reports/browser.json
python scripts/browser_cycle.py --output evidence/matrices/browser-run-001 --rounds 20
```

The browser matrix includes native and polling watchers for all three mutation modes and an expected-stale disabled-watcher control. This fixture tests dependency-accept HMR; other applications may need their own fixture and DOM oracle.

### WSL2 and Windows-origin writes

Run these commands **inside Linux in WSL2** from this project's directory. The bootstrap currently supports Linux x86_64, Python 3.12 or newer, network access, and Node 24.18.0. It verifies the official Node archive checksum, installs dependencies in a temporary Linux lab, and records toolchain provenance. The generic runner itself still supports Python 3.10+.

```sh
python3 scripts/wsl_vite_lab.py --setup-and-test
python3 scripts/wsl_vite_lab.py --test-existing
python3 scripts/wsl_vite_lab.py --matrix
python3 scripts/wsl_vite_lab.py --windows-mutations --rounds 20
python3 scripts/wsl_vite_lab.py --windows-mutations --rounds 20 --mounted-windows
```

The mounted option requires the project to be on a Windows drive mounted in WSL2. These mutations invoke Windows PowerShell against isolated fixture copies. UNC writes to the Linux filesystem and Windows writes to mounted NTFS are different experiments. The tested mounted-NTFS native watcher stayed stale; polling passed, consistent with [Vite's documented WSL2 limitation](https://vite.dev/config/server-options#server-watch).

## Scenario format

```json
{
  "fixture_dir": "examples/fixture",
  "command": ["{python}", "{config_dir}/examples/polling_generator.py", "{workspace}/input.txt", "{workspace}/output.txt"],
  "mutation_target": "input.txt",
  "mutation": "overwrite",
  "oracle": {"type": "file", "path": "output.txt"},
  "timeout_seconds": 3,
  "probe_interval_seconds": 0.03,
  "stable_seconds": 0.1
}
```

The command is an argv array, run without a shell from the temporary workspace. Placeholders are `{workspace}`, `{config_dir}`, `{python}`, `{node}`, and `{port}`. `fixture_dir` is resolved relative to the config. The target and file oracle paths must stay inside the copied fixture workspace. Optional `workspace_parent` chooses an existing directory for isolated copies, useful for testing a specific filesystem. The runner executes the configured command, so use scenarios you trust.

`oracle.type` may be `file` with a relative `path`, or `http` with a `url`. By default the response must equal the mutated input bytes. Responses are capped at 1 MiB; `oracle.max_output_bytes` can set a limit from 1 byte to 64 MiB. HTTP reads run in a disposable worker so a trickling body cannot indefinitely extend observation. For a transformed response, `oracle.extract_regex` must contain exactly one capture group; only that captured byte string is compared with the expected token.

`mutation_template` can wrap each token in valid source code and then requires `initial_expected` for the fixture baseline. An optional `version_command` records the tool's version. Mutation modes are `overwrite`, `atomic_replace`, and `burst` (an intermediate write followed immediately by the final write). Each round uses a unique token, so an old output cannot accidentally pass a later round. Optional `startup_timeout_seconds` defaults to `timeout_seconds`; the stable window must fit inside both budgets.

An optional `mutation_command` argv replaces the built-in write. It also supports `{target}`, `{mode}`, `{content_base64}`, and `{intermediate_base64}`. Its deadline is `mutation_timeout_seconds` (default 10). A nonzero exit or timeout is inconclusive rather than a watch-tool failure. Mutator diagnostics and version-command output are bounded.

Windows commands start inside a guardian Job Object; Linux commands use a process group. Cleanup covers ordinary descendants even after their launcher exits. Deliberately detached processes and cross-OS process escape are outside that containment contract. This is a test harness for trusted commands, not an executable sandbox.

## What a result means

- `pass`: exact expected bytes stayed visible for the configured stable window before the deadline.
- `stale`: readable output existed but never reached a stable exact match by the deadline.
- `timeout`: output was never readable by the deadline.
- `inconclusive`: the process exited, baseline did not become ready, output could not be extracted within policy, or an external mutation failed.

The timeout is a scenario policy, not a proof that a tool will never update. Output observed after the deadline or after process exit cannot pass. OS scheduling and file reads can add wall-clock overhead; this is not a real-time system. The short stable window cannot prove output stays correct indefinitely. An HTTP oracle observes response bytes; the separate browser adapter observes DOM state. The sample report records the earlier Windows toy run; current evidence is in the linked results and test log.

Latency measurement begins after mutation returns. An external mutator's duration is recorded separately, so those observation latencies do not measure the entire cross-OS write and rebuild path.

## Research boundary and go/no-go

Vite already has browser-level HMR integration tests and runs its test watcher in polling mode. Watchwoman already has a black-box harness for Watchman protocol parity. This pilot tests a narrower reusable question: can one external command's final file or HTTP bytes be checked after controlled mutations, independent of its watcher implementation? It has not demonstrated a gap in either project's test suite yet.

The [experiment plan](docs/experiment-plan.md) sets the matrix and decision rule. [Current results](docs/current-results.md) include Windows, Linux within WSL2, Windows-origin writes on both filesystem paths, and Windows Chrome HMR. Bare-metal Linux and other browser environments remain unverified. Continue as a standalone project only if a reproducible supported-workflow failure escapes existing tests, or at least two maintainers confirm the harness is useful. Otherwise contribute focused fixtures to existing suites. That research go/no-go criterion has not yet been met.

## License

MIT; see [LICENSE](LICENSE).

Sources: [Vite contributing guide](https://github.com/vitejs/vite/blob/main/CONTRIBUTING.md), [Vite watcher options and WSL2 warning](https://vite.dev/config/server-options#server-watch), [Watchwoman repository](https://github.com/radiosilence/watchwoman).
