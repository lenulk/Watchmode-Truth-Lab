# Watchmode Truth Lab

An experimental, black-box CLI that checks whether a watch process produces the latest **observable bytes** after a source file changes. It does not count filesystem events or infer their cause.

## Try it

Requires Python 3.10 or newer. From this directory:

```sh
python -m watchmode_truth_lab example.json --rounds 3 --mutation atomic_replace --report reports/example.json
python -m unittest discover -s tests -v
```

`example.json` starts a tiny polling generator in a copied temporary fixture. The CLI waits for its baseline output, mutates `input.txt`, and waits for exact output bytes to match the final mutation for a short stable window. Exit code 0 means all rounds passed; 1 means a freshness check failed or was inconclusive; 2 means CLI input was invalid. The JSON includes hashes, latency to the first stable match, sample counts, environment, logs, and a reproduction command/config. Scenario metadata uses a filename and SHA-256 instead of an absolute config path. Child-process logs may still contain local paths or other sensitive data, so review reports before publishing. Run reproduction commands from the directory containing the scenario.

## Run against Vite

Install the pinned Vite 8.3.1 dependency with `pnpm install --frozen-lockfile` and ensure Node.js is on `PATH`. Then run from this directory:

```sh
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation overwrite --report reports/vite-native-overwrite.json
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation atomic_replace --report reports/vite-native-atomic.json
python -m watchmode_truth_lab vite.native.json --rounds 20 --mutation burst --report reports/vite-native-burst.json
python -m watchmode_truth_lab vite.polling.json --rounds 20 --mutation overwrite --report reports/vite-polling-overwrite.json
```

The fixture serves `/src/token.js` through Vite. The oracle extracts the exported token from the transformed HTTP response. This exercises Vite's server-side module invalidation after a watched change. It does not verify browser HMR state. The polling scenario is a control for the documented watcher option. Reports are ignored by Git by default; save the ones used as evidence separately.

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

The command is an argv array, run without a shell from the temporary workspace. Placeholders are `{workspace}`, `{config_dir}`, `{python}`, `{node}`, and `{port}`. `fixture_dir` is resolved relative to the config. The target and file oracle paths must stay inside the copied fixture workspace. The runner executes the configured command, so use scenarios you trust.

`oracle.type` may be `file` with a relative `path`, or `http` with a `url`. By default the response must equal the mutated input bytes. For a transformed response, `oracle.extract_regex` must contain exactly one capture group; only that captured byte string is compared with the expected token. `mutation_template` can wrap each token in valid source code and then requires `initial_expected` for the fixture baseline. An optional `version_command` records the tool's version. Mutation modes are `overwrite`, `atomic_replace`, and `burst` (an intermediate write followed immediately by the final write). Each round uses a unique token, so an old output cannot accidentally pass a later round. The runner waits for baseline before mutating and attempts to stop the launched process tree during cleanup.

## What a result means

- `pass`: exact expected bytes stayed visible for the configured stable window before the deadline.
- `stale`: readable output existed but never reached a stable exact match by the deadline.
- `timeout`: output was never readable by the deadline.
- `inconclusive`: the process exited or the baseline did not become ready.

The timeout is a scenario policy, not a proof that a tool will never update. An HTTP oracle observes the response bytes, not browser HMR application. The short stable window cannot prove output stays correct indefinitely. Mutations run from the same OS/process as this CLI; the Windows-editor-to-WSL2 case needs a separate host-side mutation adapter. The sample report records a Windows run of the toy generator. Generic tests also pass inside WSL2, while Vite there remains untested because Node.js is not installed in that distro.

## Research boundary and go/no-go

Vite already has browser-level HMR integration tests and runs its test watcher in polling mode. Watchwoman already has a black-box harness for Watchman protocol parity. This pilot tests a narrower reusable question: can one external command's final file or HTTP bytes be checked after controlled mutations, independent of its watcher implementation? It has not demonstrated a gap in either project's test suite yet.

The [experiment plan](docs/experiment-plan.md) sets the matrix and decision rule. The [Windows Vite results](docs/windows-results-2026-09-30.md) record 20 passing rounds for each watcher and mutation combination. Next evidence: run the same matrix on Linux, compare with Vite's existing tests, then add a host-side WSL2 mutation adapter. Continue as a standalone project only if a reproducible supported-workflow failure escapes existing tests, or at least two maintainers confirm the harness is useful. Otherwise contribute focused fixtures to existing suites. A clean run does not prove absence of bugs.

## License

MIT; see [LICENSE](LICENSE).

Sources: [Vite contributing guide](https://github.com/vitejs/vite/blob/main/CONTRIBUTING.md), [Vite watcher options and WSL2 warning](https://vite.dev/config/server-options#server-watch), [Watchwoman repository](https://github.com/radiosilence/watchwoman).
