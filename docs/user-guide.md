# User guide

Watchmode Truth Lab checks observable output after a controlled file change. Use it for a generator/compiler's output file, a development server's HTTP response, or DOM updates through the Vite browser adapter. It runs trusted commands in an isolated fixture copy and records why each check passed or failed.

## Install and first run

Download the wheel from this repository's GitHub release. Python 3.10 or newer is required. Use a virtual environment; on Debian, the OS's `python3-venv` package provides pip-enabled venv creation if it is missing.

Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install /path/to/watchmode_truth_lab-1.0.0-py3-none-any.whl
.venv/bin/python -m watchmode_truth_lab --init demo --template file
cd demo
../.venv/bin/python -m watchmode_truth_lab scenario.json --validate
../.venv/bin/python -m watchmode_truth_lab scenario.json --doctor
../.venv/bin/python -m watchmode_truth_lab scenario.json --rounds 20 --mutation atomic_replace --format summary --report reports/result.json
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install C:\downloads\watchmode_truth_lab-1.0.0-py3-none-any.whl
.\.venv\Scripts\python.exe -m watchmode_truth_lab --init demo --template file
Set-Location demo
..\.venv\Scripts\python.exe -m watchmode_truth_lab scenario.json --validate
..\.venv\Scripts\python.exe -m watchmode_truth_lab scenario.json --doctor
..\.venv\Scripts\python.exe -m watchmode_truth_lab scenario.json --rounds 20 --mutation atomic_replace --format summary --report reports/result.json
```

The installed `watchmode-truth-lab` console command accepts the same options. Explicit interpreter paths above avoid shell activation requirements. Create starters from a separate project directory: invoking `python -m` from a source checkout can import that checkout instead of the installed version.

## Choose a starter

| Template | Output checked | Extra setup |
| --- | --- | --- |
| `file` | Polling sample generator output bytes | None; replace its command/fixture to test your generator |
| `vite-http` | Token in a real Vite-transformed module response | Node and pnpm; frozen dependency install |
| `vite-browser` | DOM token, no page reload, retained counter state | Same dependencies plus a supported browser and its OS libraries |

`--init` requires a new destination and never overwrites an existing project. Its parent directory must already exist. Starters include a local README. Vite starters also include `polling.json` and `disabled.json`; the latter should return stale/exit 1 and is a control, not a newly discovered tool defect.

The `file` starter is a tiny sample worker. It retries missing-source reads and, on Windows, access-denied reads (`EACCES`) for up to one second during a continuous outage. A successful read resets that retry window; an error that persists past it propagates and stops the sample. This example policy does not promise that production watchers handle file replacement the same way.

For a Vite starter, install Node (verification uses 24.18.0) and pnpm 11.19.0. Run `pnpm install --frozen-lockfile` inside the generated project. Vite 8.3.1 and Playwright Core 1.62.1 are pinned in the supplied manifest/lockfile. Use the Node engine policy of the installed Vite version when choosing another Node version.

Generated Vite starters use `server.watch.awaitWriteFinish` with a 200ms file-size stability window and 20ms checks. Native and polling modes both include this policy, which adds latency and avoids short truncate/write intervals. Adjust or remove it when testing an application's actual save policy; interrupted writes longer than the window can still expose incomplete content. Historical checkout research scenarios use their own unfiltered configuration. Other watcher backends, including experimental bundled dev, need separately verified options.

For browser verification, installed Chrome is the default Chromium channel; `WTL_BROWSER_CHANNEL=msedge` selects installed Edge. Alternatively run `pnpm exec playwright-core install chromium`, then select `WTL_BROWSER_CHANNEL=chromium`. On Linux the selected browser also needs shared libraries; `pnpm exec playwright-core install-deps chromium` is a system dependency setup command requiring appropriate privileges. Install Firefox/WebKit builds and matching dependencies only when selecting those engines.

Linux browser selection:

```sh
WTL_BROWSER_CHANNEL=chromium ../.venv/bin/python -m watchmode_truth_lab scenario.json --doctor
WTL_BROWSER_CHANNEL=chromium ../.venv/bin/python -m watchmode_truth_lab scenario.json --rounds 20 --report reports/browser.json
# After installing the matching engine:
WTL_BROWSER_ENGINE=firefox ../.venv/bin/python -m watchmode_truth_lab scenario.json --doctor
```

PowerShell uses environment assignments, for example `$env:WTL_BROWSER_CHANNEL='msedge'`, before invoking the command. Browser diagnostics launch and close a bounded browser probe; they do not start the watched Vite process or mutate its fixture. A ready diagnostic is a dependency check, not a freshness result.

## Adapt to an application

Copy a representative fixture and point `command` at your watch command. Keep commands as argv arrays. Set `mutation_target`, optional valid-source `mutation_template`/`initial_expected`, oracle and timing policy. Read [the scenario reference](../README.md#scenario-format). The target and file oracle must stay inside the fixture copy. Use `workspace_parent` to choose the storage under test. Keep credentials and live data out of fixtures intended for distribution.

The Vite browser adapter can observe an ordinary application without fixture-owned globals:

- `WTL_DOM_SELECTOR`: DOM token selector; default `#token`.
- `WTL_CLICK_SELECTOR`: optional single initial user interaction.
- `WTL_STATE_SELECTOR`: optional text whose value must remain unchanged after that interaction.
- The adapter creates an opaque identity for each document and fails if navigation replaces that document or the selected state is lost.
- If the application exposes `window.__wtl_updates`, the metric is labeled `application_hmr_callbacks`; otherwise updates are sampled DOM changes, labeled `observed_dom_changes`. Do not interpret the latter as framework callback counts.

After launching the browser, the adapter gives readiness a fixed 10-second total budget. Navigation retries, waiting for the document identity, token and optional state, and the optional initial click all share that budget. Generated browser scenarios set an outer `startup_timeout_seconds` of 15 seconds; increasing that outer timeout does not extend the adapter's internal 10-second budget.

The generated application imports a token, view module and CSS, clicks its counter, then checks the DOM and retained counter through native/polling updates. Other frameworks, routes, authentication flows or state contracts need their own acceptance scenario. HTTP output alone does not establish browser HMR.

## Commands and outcomes

| Option/action | Meaning |
| --- | --- |
| `--version` | Installed tool version |
| `--init DIR --template NAME` | Create a runnable starter |
| `scenario.json --validate` | Validate configuration/paths without starting commands or mutating files |
| `scenario.json --doctor` | Inspect executable/assets/dependencies and selected browser availability |
| `--rounds N --mutation MODE` | Positive round count; overwrite, atomic_replace or burst |
| `--format json` | Default machine-readable console JSON |
| `--format summary` | Short readable console result; saved report remains JSON |
| `--report PATH` | UTF-8 JSON export, staged before replacing an existing report |

Exit 0 means checks passed, validation succeeded, starter was created or diagnostics are ready. Exit 1 means freshness failed/inconclusive. Exit 2 means invalid configuration, missing diagnosed dependencies or report export failure. Controlled SIGINT returns 130 after runner teardown. A canceled run has no completed new report; inspect the exit code rather than an older report already on disk.

Read overall status, startup result, per-round reason and logs together. [Report semantics](report-format.md) explain deadlines, stale controls and process failures. Sampling cannot prove continuous correctness; time budgets are scenario policies. Run reproduction commands from the scenario directory with the same installed version, dependencies and environment.

## Troubleshooting and upgrades

- `--validate` failure: fix the named configuration field/path first.
- `--doctor` failure: install/correct the listed executable, pinned dependencies or browser libraries. Re-run diagnostics before the freshness check.
- Startup inconclusive: inspect command logs and startup budget independently of mutation observation budget.
- Readable old output: compare native/polling and the supported editing/storage workflow. The recorded WSL2 Windows-mounted-storage native limitation is described in [current results](current-results.md).
- Extraction/body-limit error: check the response format, regex's single capture group and size cap before assigning blame to the watcher.
- Export failure: choose a writable file destination. The prior file is retained if staging/replacement fails; no successful new export is claimed.
- Setup EPERM on Windows: keep creation/install/execution under the same user identity; staged files may inherit creator-specific permissions.

Upgrade by installing the new wheel in a separate venv, running your existing scenario/control there, then switching your invocation. Keep the previous venv and wheel for rollback; preserve scenario files/reports. Check [release notes](../CHANGELOG.md) and report/CLI compatibility before changing versions. Inspect logs and configuration inputs before sharing reports; arbitrary watched commands can emit sensitive data.
