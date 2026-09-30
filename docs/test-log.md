# Test and improvement log

Every new automated cycle saves JSON and text output using `scripts/test_cycle.py`. Experimental scenarios save their own JSON reports. Entries below explain what the evidence establishes and what remains unresolved.

## Prior evidence

The initial project committed in `35ee9f1` passed seven tests on Windows and six generic tests in WSL2, with Vite skipped there. Six Vite scenarios on Windows each passed 20 rounds. The retained scenario reports are in `evidence/windows-2026-09-30/`. Original unittest console output was not persisted; subsequent cycles use the recording script.

## Initial investigation queue (resolved in the cycles below)

1. Oracle deadline and process-liveness decisions: a matching sample can currently return `pass` before checking whether the process exited or the deadline expired. Confirm with controlled tests.
2. Probe limits: HTTP bodies can be unbounded; file/HTTP probe errors and slow responses need explicit outcomes.
3. Cleanup after a launcher exits: child processes may survive because cleanup returns when the parent has exited. Verify before choosing a platform-specific fix.
4. Configuration boundaries: missing command, non-string mutation modes, and timing policies need controlled CLI error behavior.
5. WSL2 real-tool coverage: provision a project-local Linux runtime and dependency copy, then run positive and deliberately stale Vite controls. Windows-to-WSL2 and browser HMR require separate evidence.

## Remaining verification queue

- Physical Linux hardware remains unverified. Linux Chromium is verified in the Debian VMware guest; WSL2 and Windows Chrome evidence remain separate.
- Chrome/Edge and Debian Chromium/Firefox/WebKit have actual browser coverage. Safari on Apple platforms, further browser/platform combinations, and application-specific HMR fixtures remain unverified.
- A supported-workflow gap in existing tests or maintainer confirmation is still needed for the research go/no-go decision.

## Cycle 1 Windows baseline

- Evidence: [JSON](../evidence/test-runs/20260930T112125Z-baseline-windows-6a1a8d.json), [console log](../evidence/test-runs/20260930T112125Z-baseline-windows-6a1a8d.log).
- Purpose and result: establish the current baseline; seven tests passed with no skips.
- Analysis: existing tests cover normal freshness, stale file output, HTTP, templated source, Vite, path containment, and nonfinite timing. They do not establish deadline correctness or process-liveness correctness at the moment of a matching observation.
- Next improvement: add controlled oracle regression tests before changing those decisions. Real WSL2 Vite coverage remains pending.

## Cycle 2 Oracle regression before repair

- Evidence: [JSON](../evidence/test-runs/20260930T112300Z-oracle-regression-before-d677b5.json), [console log](../evidence/test-runs/20260930T112300Z-oracle-regression-before-d677b5.log).
- Result: two of three controlled simulations failed. The current code returned `pass` for a matching output from an exited process and for a matching output first observed after the deadline. A transient match followed by old output was correctly rejected.
- Analysis and repair: `_wait` returns from the match branch before checking process liveness and the deadline. Move both guards before the pass decision and distinguish a late matching observation from stale output.
- Remaining risk: probe calls themselves may consume more than the remaining deadline; investigate in a separate cycle.

## Cycle 3 Oracle regression after repair

- Evidence: [JSON](../evidence/test-runs/20260930T112401Z-oracle-regression-after-b7e727.json), [console log](../evidence/test-runs/20260930T112401Z-oracle-regression-after-b7e727.log).
- Result: all three controlled simulations passed.
- Analysis: a matching sample now requires a live watch process and an observation before the deadline. This addresses false passes; it does not yet bound the duration of an HTTP read.
- Next improvement: exercise a real HTTP server that slowly trickles body bytes and verify total observation time.

## Cycle 4 HTTP deadline before repair

- Evidence: [JSON](../evidence/test-runs/20260930T112620Z-http-deadline-before-7938b3.json), [console log](../evidence/test-runs/20260930T112620Z-http-deadline-before-7938b3.log).
- Result: the controlled real HTTP test failed. A 200 ms observation deadline took about 1.484 seconds because the response trickled body bytes without triggering the socket inactivity timeout.
- Analysis and repair: isolate HTTP reads in a persistent probe process. The parent polls with the remaining deadline and terminates a blocked probe. Limit file and HTTP output size to 1 MiB by default, configurable up to 64 MiB.
- Remaining risk: termination overhead and platform scheduling are bounded separately; a deadline is not a real-time scheduling guarantee. File reads still depend on local OS storage latency.

## Cycle 5 HTTP deadline after repair

- Evidence: [JSON](../evidence/test-runs/20260930T112918Z-http-deadline-after-adfa87.json), [console log](../evidence/test-runs/20260930T112918Z-http-deadline-after-adfa87.log).
- Result: all five focused tests passed, including the real trickling HTTP body, oversized response rejection, and prior oracle decision regressions.
- Analysis: blocking HTTP work is isolated and can be terminated within the parent observation budget. The process is reused for normal samples; latency includes process communication and probe startup when applicable.
- Next improvement: verify the existing file, HTTP, and Vite integrations on both Windows and WSL2 before investigating process-tree cleanup.

## Cycle 6 Integration after probe isolation

- Evidence: [Windows JSON](../evidence/test-runs/20260930T113118Z-integration-after-probe-windows-c88a11.json), [WSL2 JSON](../evidence/test-runs/20260930T113129Z-integration-after-probe-wsl2-c404eb.json); accompanying `.log` files preserve the console output.
- Result: Windows passed all 12 tests. WSL2 passed 11 and skipped the Vite dependency test because Linux Node is unavailable.
- Analysis: bounded HTTP probes preserve the existing identity, templated file, and Vite module-response integrations. The skip is an environment limitation, not a passing Vite/WSL2 result.
- Next improvement: verify whether a launcher can leave children running after it exits.

## Cycle 7 Cleanup before repair

- Evidence: [Windows JSON](../evidence/test-runs/20260930T113253Z-cleanup-before-windows-6bda02.json), [WSL2 JSON](../evidence/test-runs/20260930T113301Z-cleanup-before-wsl2-43fb53.json).
- Result: Windows raised a fixture cleanup error because a child retained the working directory; WSL2 confirmed a child remained alive after the launcher exited.
- Analysis and repair: cleanup previously returned when the root process exited. POSIX cleanup now signals the process group even after launcher exit. On Windows, a Python guardian establishes a kill-on-close Job Object before it launches the configured command, avoiding a race between command startup and job assignment.
- Remaining risk: intentionally detached POSIX descendants that create a new session and Windows children created through mechanisms that bypass job inheritance are outside the current process containment contract. Microsoft documents job behavior in [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
- Evidence handling: escaped absolute paths in exception strings exposed a redaction gap in the test recorder. The redactor now handles escaped paths too; saved failure traces are redacted without changing test outcomes.

## Cycle 8 Cleanup after repair

- Evidence: [Windows JSON](../evidence/test-runs/20260930T113603Z-cleanup-after-windows-697d27.json), [WSL2 JSON](../evidence/test-runs/20260930T113612Z-cleanup-after-wsl2-9acbf3.json).
- Result: the exited-launcher child regression passed on both systems. Windows also cleaned its temporary fixture successfully.
- Analysis: ordinary descendants are contained before the configured command starts on Windows; POSIX cleanup addresses the group after launcher exit. Intentionally detached process behavior remains outside this test.
- Next improvement: make malformed scenarios fail through the documented CLI error path.

## Cycle 9 CLI configuration before repair

- Evidence: [JSON](../evidence/test-runs/20260930T113757Z-cli-config-before-fad298.json), [console log](../evidence/test-runs/20260930T113757Z-cli-config-before-fad298.log).
- Result: all four malformed-scenario subcases failed the expected exit-code check. Missing command and list-valued modes escaped validation; an impossible stability duration was allowed to start a process.
- Analysis and repair: validate command lookup and mode/type values before membership checks and reject a stability window that cannot fit inside its observation deadline.
- Remaining risk: scenario commands remain trusted executable input; these checks are input validation, not a general executable sandbox.

## Cycle 10 CLI configuration after repair

- Evidence: [JSON](../evidence/test-runs/20260930T113841Z-cli-config-after-9f9d50.json), [console log](../evidence/test-runs/20260930T113841Z-cli-config-after-9f9d50.log).
- Result: the four malformed-scenario subcases now pass the documented exit-code and no-traceback checks.
- Analysis: impossible timing policies and invalid structural values fail before command startup. Valid integrations must be rechecked after the guardian change.
- Next improvement: provision an isolated Linux runtime for real Vite verification in WSL2 and use a disabled-watcher control.

## Cycle 11 Windows integration after guardian

- Evidence: [JSON](../evidence/test-runs/20260930T113917Z-integration-after-guardian-windows-20d3cc.json), [console log](../evidence/test-runs/20260930T113917Z-integration-after-guardian-windows-20d3cc.log).
- Result: all 14 tests passed, including Vite, launcher cleanup, slow HTTP, and malformed CLI inputs.
- Analysis: the guardian works in this Windows environment and does not disrupt normal Vite responses. Test runtime also decreased because cleanup no longer waits for a failed `taskkill` fallback.
- Next improvement: a real disabled-watcher control must report stale output, then run equivalent Linux Vite tests in WSL2.

## Cycle 12 Windows Vite negative control

- Evidence: [JSON](../evidence/test-runs/20260930T114116Z-vite-negative-control-windows-c16fd6.json), [console log](../evidence/test-runs/20260930T114116Z-vite-negative-control-windows-c16fd6.log).
- Result: the test passed: Vite startup served the initial token, then disabling `server.watch` caused the mutation to be correctly reported as `stale`.
- Analysis: this controlled failure demonstrates detector sensitivity for this module endpoint. Disabling the watcher is deliberate unsupported test behavior, not a newly discovered Vite bug.
- Next improvement: provision Linux-only dependencies in a temporary WSL2 lab and repeat positive and negative controls.

## Cycle 13 Linux Vite in WSL2

- Evidence: [JSON](../evidence/test-runs/20260930T114525Z-linux-vite-wsl2-c29938.json), [console log](../evidence/test-runs/20260930T114525Z-linux-vite-wsl2-c29938.log), [toolchain provenance](../evidence/wsl2-toolchain.json).
- Result: all 15 tests passed with no skips, including real Linux Vite and its disabled-watcher stale control.
- Analysis: Linux Node 24.18.0 and Vite 8.3.1 were installed in a temporary WSL2 lab from the project's frozen lockfile; the Node archive was checked against its official SHA-256 manifest. These results establish Linux-side editing within WSL2, not Windows-origin edits or bare-metal Linux behavior.
- Next improvement: repeat the mutation/watcher matrix with the repaired runner and persist an assessment for every scenario.

## Cycle 14 Repaired-runner Vite matrix

- Evidence: [Windows summary](../evidence/matrices/windows-repaired-2026-09-30/summary.json), [WSL2 Linux-side summary](../evidence/matrices/wsl2-linux-side-2026-09-30/summary.json). Every adjacent scenario JSON contains the report, expected outcome, assessment, and analysis.
- Result: all six positive scenarios passed 20/20 rounds on each system (240 positive rounds total). Both disabled-watcher controls returned the expected stale outcome.
- Analysis: the repaired runner preserves endpoint freshness checks and detects deliberate stale output across Windows and Linux within WSL2. Probes and scheduling contribute to observed latency; concurrent environment runs were not a performance benchmark.
- Next improvement: add a Windows-origin mutation adapter that edits an isolated WSL2 fixture through its UNC share. This must be recorded separately from Linux-origin edits and must not be described as fixing a WSL2 limitation.

## Cycle 15 External mutation interface

- Evidence: [JSON](../evidence/test-runs/20260930T115305Z-external-mutation-windows-202d74.json), [console log](../evidence/test-runs/20260930T115305Z-external-mutation-windows-202d74.log).
- Result: both successful and failing external-mutator subcases passed. A nonzero mutator exit is inconclusive even if it wrote bytes that happened to match.
- Analysis: external writes can be distinguished from watch-tool failures, and the external command uses the same process containment mechanism as the watch process.
- Next improvement: use a Windows PowerShell mutator through a WSL2 UNC path and retain origin/path details in each experiment assessment.

## Cycle 16 Windows-origin WSL2 UNC smoke

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-unc-20260930T115618Z/summary.json), with six per-scenario reports and mutator return codes.
- Result: all six watcher/mutation combinations passed three rounds each (18 rounds) when a Windows PowerShell process edited the Linux filesystem through its WSL2 UNC share.
- Analysis: cross-origin edits work for this tested UNC/Linux-filesystem path. This result does not apply to Windows NTFS mounted at `/mnt/c`, where event propagation has different behavior.
- Next improvement: repeat the UNC matrix at 20 rounds and add a distinct mounted-NTFS path. Preserve any native-watcher stale observation as an environment-specific result, not evidence of a new Vite bug.

## Cycle 17 Windows-origin mounted NTFS smoke

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T115914Z/summary.json), with six scenario reports.
- Result: all nine native-watcher rounds returned stale; all nine polling rounds passed. All mutator commands completed successfully.
- Analysis: this supported observation reproduces the documented Windows-origin `/mnt/c` limitation. It is environment-specific evidence, not a newly discovered Vite defect. UNC/Linux-filesystem results remain separate.
- Next improvement: repeat both paths at 20 rounds. Use an explicit two-second post-mutation deadline and a separate eight-second startup budget so repeated known stale cases do not conflate startup and mutation policies.

## Cycle 18 Windows-origin WSL2 UNC repeat

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-unc-20260930T120225Z/summary.json), with six scenario reports and successful external-mutator return codes.
- Result: all six combinations passed 20/20 rounds (120 rounds) with a two-second observation deadline and eight-second startup budget.
- Analysis: Windows PowerShell writes through the UNC share propagated to Vite running on the Linux filesystem in this WSL2 environment. This is endpoint freshness evidence; browser HMR and mounted Windows NTFS remain distinct checks.
- Next improvement: repeat the mounted-NTFS matrix with the same timing policy, retaining native stale observations and polling outcomes separately.

## Cycle 19 Windows-origin mounted NTFS repeat

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T125228Z/summary.json), with successful mutator commands and per-round hashes.
- Result: native watching returned stale in all 60 rounds; polling passed all 60 rounds, across overwrite, atomic replacement, and burst.
- Analysis: this repeat reproduces the documented WSL2 event limitation for Windows-origin writes on mounted Windows NTFS. It does not establish a new Vite bug. Native watching on the separately tested UNC/Linux-filesystem path passed.
- Next improvement: test actual browser DOM updates and session continuity; endpoint freshness alone cannot establish browser HMR delivery.

## Cycle 20 Chrome HMR integration

- Evidence: [JSON](../evidence/test-runs/20260930T125640Z-browser-hmr-windows-ce32b3.json), [console log](../evidence/test-runs/20260930T125640Z-browser-hmr-windows-ce32b3.log).
- Result: both browser tests passed without skips. Atomic replacements updated the actual DOM twice with one page session; the disabled-watcher control retained the seed and returned stale.
- Change: added a separate browser fixture and an adapter using pinned Playwright Core 1.62.1 with the existing installed Chrome. The adapter rejects a changed page session rather than treating a reload as HMR success.
- Analysis and limit: this verifies a controlled Vite dependency-accept HMR path on Windows Chrome. Other browsers, Linux browser execution, and application-specific HMR state remain unverified.
- Next improvement: repeat all three mutation modes with native and polling watching in Chrome, with a deliberately stale browser control.

## Cycle 21 Browser matrix exposed a Windows adapter race

- Evidence: [failed scenario](../evidence/matrices/windows-chrome-hmr-2026-09-30/native-overwrite.json), [partial summary](../evidence/matrices/windows-chrome-hmr-2026-09-30/summary.json).
- Result: six DOM updates passed, then the adapter exited on an `EPERM` while atomically replacing its observation file. The matrix stopped and retained its failure.
- Analysis: the Python oracle can briefly hold the destination open on Windows while the Node adapter renames its next snapshot. This is an adapter publication race, not a demonstrated Vite HMR failure. The page session remained unchanged through the six observed updates.
- Repair: retry only transient Windows rename permission/busy errors for a bounded interval; retain failure for other errors. Also extend evidence path redaction for multiply escaped Windows paths found in this diagnostic, preserving recorded outcomes.
- Next verification: repeat the complete browser matrix in a new evidence directory, then check positive and disabled-watcher integration tests.

## Cycle 22 Repaired Chrome HMR matrix

- Evidence: [summary](../evidence/matrices/windows-chrome-hmr-repaired-2026-09-30/summary.json), with DOM states, browser version, HMR update counts, and page session continuity per scenario.
- Result: all six positive scenarios passed 20/20 rounds (120 DOM updates) in Chrome 154.0.8037.58. Every positive run retained one page session and observed at least 20 HMR callbacks. The disabled-watcher control correctly returned stale with zero HMR callbacks.
- Analysis: bounded rename retries resolved the observed adapter publication race for this matrix. Windows Chrome now has real browser evidence distinct from HTTP endpoint checks. Other browser and Linux browser environments remain unverified.
- Next improvement: ensure a matrix cannot overwrite previously saved evidence, then review resource bounds and perform final Windows/WSL2 regression checks.

## Cycle 23 Evidence preservation before repair

- Evidence: [JSON](../evidence/test-runs/20260930T130149Z-evidence-preservation-before-4c952b.json), [console log](../evidence/test-runs/20260930T130149Z-evidence-preservation-before-4c952b.log).
- Result: the simulated preservation test errored after the scenario function was called instead of rejecting the existing directory. Its mock result also lacked a serializable report; no real scenario ran and the temporary marker was isolated.
- Analysis and repair: the ordinary matrix used `exist_ok=True`, permitting old evidence to be overwritten. Reject an existing directory before any scenarios, matching the browser and cross-origin matrix scripts. Give the mock a concrete report for a precise regression assertion.
- Next verification: the existing-directory case must raise before execution and retain the original marker bytes.

## Cycle 24 Evidence preservation after repair

- Evidence: [JSON](../evidence/test-runs/20260930T130245Z-evidence-preservation-after-8ff31b.json), [console log](../evidence/test-runs/20260930T130245Z-evidence-preservation-after-8ff31b.log).
- Result: the regression passed: an existing matrix directory is rejected before running a scenario and its original summary bytes remain intact.
- Analysis: new matrix runs require a fresh directory, preserving previous positive and failed cycles. Test-cycle artifacts already use timestamp plus random identifiers.
- Next improvement: check bounded log reads; limiting retained lines alone does not prevent an oversized single line from being allocated.

## Cycle 25 Bounded logging before repair

- Evidence: [JSON](../evidence/test-runs/20260930T130348Z-bounded-log-before-7d0c8d.json), [console log](../evidence/test-runs/20260930T130348Z-bounded-log-before-7d0c8d.log).
- Result: the simulated two-MiB-line regression failed because capture requested an unbounded `readline()` before truncating retained text.
- Analysis and repair: cap each read, drain the remainder of long lines, and retain the next diagnostic. Use the same bounded threaded capture for external mutators and version commands instead of `communicate()`/`capture_output`, which collect unlimited output.
- Next verification: verify oversized lines, a real noisy mutator, mutator timeout, and ordinary successful/failing mutations.

## Cycle 26 Bounded logging after repair

- Evidence: [JSON](../evidence/test-runs/20260930T130542Z-bounded-log-after-344305.json), [console log](../evidence/test-runs/20260930T130542Z-bounded-log-after-344305.log).
- Result: all three tests passed, including a simulated two-MiB line and real subprocesses that emit two MiB, succeed, fail, or exceed the mutation deadline.
- Analysis: capture drains long lines with bounded reads while preserving later diagnostics. External mutation and version commands now use bounded capture and the same process containment. Timeout remains inconclusive, and diagnostics retain at most 2,000 characters.
- Next verification: run the complete suite on Windows and on Linux within the existing WSL2 lab, then check representative cross-origin integrations after the command-capture change.

## Cycle 27 Windows final regression

- Evidence: [JSON](../evidence/test-runs/20260930T130654Z-final-windows-7d98e7.json), [console log](../evidence/test-runs/20260930T130654Z-final-windows-7d98e7.log).
- Result: all 21 tests passed with no failures, errors, or skips. This includes real Chrome HMR, Vite positive/stale controls, launcher cleanup, bounded HTTP and logs, CLI boundaries, and external mutation outcomes.
- Analysis: the command-capture repair preserves the verified Windows integrations, including tool-version capture and browser state diagnostics. The suite contains both controlled simulations and real subprocess/browser checks; it does not establish all possible environments.
- Next verification: run the equivalent generic and Vite integrations with Linux Node in WSL2; browser tests must be reported as skipped there because Linux browser execution is not provisioned.

## Cycle 28 WSL2 final regression

- Evidence: [JSON](../evidence/test-runs/20260930T130852Z-final-linux-wsl2-f136bd.json), [console log](../evidence/test-runs/20260930T130852Z-final-linux-wsl2-f136bd.log).
- Result: 19 tests passed, two browser tests skipped, and no failures or errors. Linux Vite, cleanup after launcher exit, bounded HTTP/log capture, CLI validation, and external mutator success/failure/timeout all passed.
- Analysis: the existing isolated Linux lab was refreshed and its dependencies installed from the updated frozen lockfile. Browser skips are explicit: these tests require installed Windows Chrome, so no Linux browser result is claimed.
- Next verification: repeat the two Windows-origin filesystem paths with two rounds per combination to verify the changed bounded external-command capture in those real integrations.

## Cycle 29 Cross-origin UNC after bounded command capture

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-unc-20260930T131405Z/summary.json), with six reports and mutator diagnostics.
- Result: all six combinations passed two rounds each (12 rounds); every external mutation command returned zero.
- Analysis: bounded capture and guardian/process-group changes preserve the real Windows PowerShell-to-Linux UNC integration. This targeted check follows the previously completed 120-round UNC matrix rather than replacing its evidence.
- Next verification: repeat the mounted-NTFS integration after the same capture change, then audit evidence and documentation links.

## Cycle 30 Cross-origin mounted NTFS after bounded command capture

- Evidence: [summary](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T131542Z/summary.json), with six reports and successful Windows mutator commands.
- Result: native watching returned stale in all six rounds; polling passed all six rounds. All three mutation modes reproduced the earlier 20-round matrix outcome.
- Analysis: the capture repair preserves the tested cross-origin integration and the detector still distinguishes the known mounted-NTFS native limitation from the working polling control.
- Next verification: audit saved JSON, matrix summary consistency, documentation links, and literal user-home paths before committing the reviewed changes.

## Cycle 31 Evidence and documentation audit

- Evidence: [JSON](../evidence/test-runs/20260930T131816Z-artifact-audit-fb3a0c.json), [console log](../evidence/test-runs/20260930T131816Z-artifact-audit-fb3a0c.log).
- Result: all three artifact checks passed: saved evidence JSON parses, matrix summaries agree with their scenario files, test reports retain console logs, local documentation links resolve, and the scanned evidence contains no literal Windows/Linux user-home path.
- Analysis: failed and skipped histories remain distinguishable from passing results. Historical pilot documentation now points to current evidence; the initial investigation queue is marked resolved, with external-environment and research-validation limits retained.
- Final review: inspect the actual source/document diff and run Git whitespace checks before a local commit. No additional behavioral change follows the passing Windows and WSL2 regressions.
- Git review: the staged check found trailing spaces in retained unittest console output. Scoped the whitespace attribute to console-evidence logs so their original formatting is preserved; source, JSON, and documentation remain checked. Approved staging also required an exact per-command `safe.directory` because the checkout belongs to the sandbox account, as recorded in engineering notes.

## Cycle 32 Missing Git on the Debian VM

- Evidence: [JSON](../evidence/test-runs/20260930T135402Z-missing-git-before-1c9fbd.json), [console log](../evidence/test-runs/20260930T135402Z-missing-git-before-1c9fbd.log).
- Observation: the SSH-connected Debian guest reports version 12.15, Python 3.11.2, VMware, and no Git executable. The transferred source archive from `da9270c` was SHA-256 verified before extraction into a fresh project directory.
- Result: the controlled missing-Git regression errored. Metadata collection raised `FileNotFoundError`, which would prevent test outcomes from being saved on this minimal VM.
- Repair: treat unavailable Git metadata as unknown, permit the verified archive revision through `WTL_SOURCE_REVISION`, and record recorder/runner hashes. Unknown working-tree state must remain null rather than being reported clean.
- Next verification: repeat the metadata regression, then run the generic suite on the VM before installing Node/browser dependencies.

## Cycle 33 Missing Git recording after repair

- Evidence: [JSON](../evidence/test-runs/20260930T135516Z-missing-git-after-de6c83.json), [console log](../evidence/test-runs/20260930T135516Z-missing-git-after-de6c83.log).
- Result: both recording regressions passed: unavailable Git metadata returns unknown, and existing matrix evidence remains protected.
- Analysis: the recorder no longer requires Git to save results. The verified archive revision and explicit file hashes make VM reports traceable while unknown working-tree state remains null.
- Next verification: transfer this focused recorder update and run the Debian VM baseline before adding tool dependencies.

## Cycle 34 Debian VM baseline before tool installation

- Evidence: [JSON](../evidence/test-runs/20260930T135641Z-debian-vm-baseline-a02eb0.json), [console log](../evidence/test-runs/20260930T135641Z-debian-vm-baseline-a02eb0.log), [observed VM environment](../evidence/debian-vm-environment.json). Artifacts are retained on the VM and collected into this project.
- Result: 18 tests passed and four tool-dependent tests were skipped, with zero failures or errors. Vite and browser dependencies are not installed yet.
- Analysis: the generic runner and corrected recorder work on Debian 12.15/Python 3.11.2 within VMware, independently of WSL2. Git metadata is unavailable rather than falsely clean. The reported filesystem label is `ext2/ext3`; no more specific type is inferred from that label.
- Provisioning preparation: retained the pre-install dpkg status and manual package list in ignored VM reports. Node/pnpm will be project-local; any browser-library additions are separately recorded.
- Next improvement: add a Linux bootstrap compatible with Python 3.11.2, whose tar API lacks the newer `filter` argument, then verify extraction boundaries before provisioning.

## Cycle 35 Portable Linux toolchain bootstrap

- Evidence: [JSON](../evidence/test-runs/20260930T140016Z-linux-bootstrap-portability-aba179.json), [console log](../evidence/test-runs/20260930T140016Z-linux-bootstrap-portability-aba179.log).
- Result: both extraction tests passed. A controlled old-Python API branch extracts regular files, and escaping members/symlink targets are rejected before extraction.
- Change and analysis: added a separate Linux bootstrap for an existing project copy. It verifies the official Node archive SHA-256 before extraction, uses newer data filtering where available, supports the observed Debian Python API, and installs Node/pnpm inside ignored project reports.
- Limit: the bootstrap is for verified official Node archives on Linux x86_64, not a general untrusted-archive extraction service.
- Next verification: provision the Debian VM from the frozen lockfile, run real Vite checks, and add Linux browser opt-in coverage after installing the required browser libraries.

## Cycle 36 Browser platform opt-in preserves Windows checks

- Evidence: [JSON](../evidence/test-runs/20260930T140333Z-browser-platform-opt-in-windows-6a5b1b.json), [console log](../evidence/test-runs/20260930T140333Z-browser-platform-opt-in-windows-6a5b1b.log).
- Result: both real Windows Chrome tests passed without skips after adding explicit Linux browser opt-in.
- Change and analysis: Linux browser tests can now be enabled with `WTL_TEST_BROWSER=1` after provisioning. The browser matrix records the selected channel and uses an environment-neutral label, preserving the earlier Windows browser behavior.
- Next verification: run the Debian suite with the newly provisioned Linux Node/Vite, then install browser dependencies and exercise the Linux opt-in in the actual VM.

## Cycle 37 Debian VM with real Vite

- Evidence: [JSON](../evidence/test-runs/20260930T140442Z-debian-vm-vite-b51038.json), [console log](../evidence/test-runs/20260930T140442Z-debian-vm-vite-b51038.log), [toolchain provenance](../evidence/debian-vm-toolchain.json).
- Result: 22 tests passed and two browser tests skipped, with zero failures or errors. Real Linux Vite freshness and its disabled-watcher stale control both passed on the VM.
- Analysis: the portable bootstrap successfully verified and extracted the official Node archive using the observed older Python API, then installed frozen dependencies. This establishes Vite in the Debian guest, separate from Windows and WSL2.
- Next verification: install Chromium libraries through root while retaining the package baseline, download the browser into ignored project storage as `test`, and enable Linux browser tests.

## Cycle 38 Debian browser dependency provisioning failed on CD-ROM source

- Evidence: [record](../evidence/debian-vm-browser-dependencies-before.json), [redacted installation log](../evidence/debian-vm-browser-dependencies-before.log).
- Result: Playwright's dependency installer failed with APT exit 100 because the active installation-CD repository has no usable release metadata for `apt-get update`.
- Analysis: this is VM provisioning configuration, not a watch-mode or browser-HMR failure. The package database is checked against the retained pre-install baseline.
- Repair plan: inspect the active CD-ROM entry, preserve `/etc/apt/sources.list`, and comment only that entry before retrying the official browser dependency installer. Retain the backup and package baseline for rollback.
- Next verification: dependency installation must succeed; record package additions/upgrades and run real Linux browser tests without counting provisioning as a browser pass.
- Baseline check: Git, git-man, and liberror-perl appeared after the original package snapshot, before the browser retry. The failed browser step stopped during APT update; these additions are not attributed to it. Preserve that existing work and take a fresh package baseline immediately before the authorized browser-library installation.

## Cycle 39 Windows regression for Debian support changes

- Evidence: [JSON](../evidence/test-runs/20260930T141238Z-debian-support-windows-regression-8b93f8.json), [console log](../evidence/test-runs/20260930T141238Z-debian-support-windows-regression-8b93f8.log).
- Result: all 24 tests passed with no skips, failures, or errors.
- Analysis: optional Git metadata, the portable Linux extraction helper, and Linux browser opt-in preserve existing Windows software and real Chrome integrations. This is a regression check on the host, separate from VM provisioning.
- Next verification: complete Debian browser provisioning and run the full VM suite and both Vite matrices.

## Cycle 40 Debian browser dependency retry reached a network failure

- Evidence: [source change and rollback record](../evidence/debian-vm-apt-source-change.json), [retry result](../evidence/debian-vm-browser-dependencies-after.json), [retry log](../evidence/debian-vm-browser-dependencies-after.log).
- Result: disabling the single inspected CD-ROM entry allowed APT update to succeed. Package downloads then failed with network-unreachable diagnostics; the dependency installer still exited 100.
- Analysis: the CD-ROM configuration issue is resolved, but no browser pass is claimed. The sources backup and a fresh package baseline were retained before the retry. Diagnose IPv4/IPv6 and HTTP/HTTPS reachability before choosing a scoped network workaround.
- Next verification: collect reachability observations, retry with an explicit supported APT configuration, and retain this failed attempt rather than overwriting it.

## Cycle 41 Debian browser libraries installed with scoped IPv4 retry

- Evidence: [network observations](../evidence/debian-vm-network-probe.json), [retry result](../evidence/debian-vm-browser-dependencies-ipv4.json), [retry log](../evidence/debian-vm-browser-dependencies-ipv4.log), [package changes and rollback references](../evidence/debian-vm-package-changes.json).
- Result: both HTTP and HTTPS metadata requests returned 200. A per-command APT configuration using IPv4, retries, and request timeouts completed browser-library installation successfully.
- Analysis: the retry resolved this observed download problem without establishing that IPv6 was its sole cause. The inspected CD-ROM source change and package baselines are recorded separately; this provisioning success is not a browser/HMR test pass.
- Next verification: download project-local Chromium as the ordinary user, run Linux browser opt-in tests, and inspect for remaining project browser processes after cleanup.

## Cycle 42 Direct VM browser download failed

- Evidence: [result](../evidence/debian-vm-browser-download-before.json), [redacted download log](../evidence/debian-vm-browser-download-before.log).
- Result: the pinned browser download exhausted retries with read timeouts and a transient DNS lookup error; installation exited 1. Browser libraries are already provisioned, but browser tests have not run.
- Analysis and recovery: fetch the exact archives named by pinned Playwright's browser manifest on the Windows host, transfer them to the guest, and verify transfer hashes. Use Playwright's supported download-host override against a temporary localhost server so its normal installer performs extraction and completion checks.
- Limit: browser archive hashes establish transfer identity to the HTTPS host download; they are not claimed as publisher signatures. Node retains its separate official SHA-256-manifest verification.
- Next verification: finish the normal browser installer from the local mirror, then run real Linux DOM/HMR tests and process cleanup inspection.

## Cycle 43 Browser installation recovered through verified local mirror

- Evidence: [archive origin and transfer hashes](../evidence/debian-vm-browser-download-provenance.json), [installation result](../evidence/debian-vm-browser-download-after.json), [installation log](../evidence/debian-vm-browser-download-after.log).
- Result: host HTTPS downloads completed for Chromium revision 1234 (Chrome for Testing 151.0.7922.34) and FFmpeg revision 1011. The guest verified both SHA-256 values and the normal Playwright installer completed successfully from the temporary localhost mirror.
- Analysis: browser binaries are project-local, and the mirror server is shut down in a finally block. This bypasses the observed guest download failure while retaining the pinned archives and installer behavior. No browser test outcome is inferred from installation alone.
- Next verification: enable Linux browser tests in the full VM suite and inspect project-local Node/Chromium processes after completion.

## Cycle 44 Full Debian VM suite with real Chromium

- Evidence: [JSON](../evidence/test-runs/20260930T143705Z-debian-vm-browser-full-bd4997.json), [console log](../evidence/test-runs/20260930T143705Z-debian-vm-browser-full-bd4997.log).
- Result: all 24 tests passed with zero skips, failures, or errors, including real Linux Chromium DOM/HMR freshness and the disabled-watcher stale control.
- Analysis: verification ran in the Debian VMware guest against the source archive based on da9270c plus the recorded support updates. Recorder and runner hashes identify the executed files. This is VM verification, separate from WSL2 and physical Linux hardware.
- Next verification: inspect remaining project Node/Chromium processes, then run repeated endpoint and browser matrices on the Linux-local filesystem.

## Cycle 45 Debian browser process cleanup

- Evidence: [JSON](../evidence/test-runs/20260930T144622Z-debian-vm-browser-cleanup-f001d9.json), [console log](../evidence/test-runs/20260930T144622Z-debian-vm-browser-cleanup-f001d9.log).
- Result: the post-experiment process check passed; no live project-local Node, Chromium, or Chromium crash-handler process was found after the full suite.
- Analysis: the check reads actual guest /proc executable paths after a bounded settling interval. It verifies the observed completed experiments; it does not promise cleanup of arbitrary detached external processes or future interrupted sessions.
- Next verification: run the repeated real Vite endpoint matrix, then the real browser HMR matrix.

## Cycle 46 Debian VM endpoint matrix

- Evidence: [summary](../evidence/matrices/debian-vm-endpoint-2026-09-30/summary.json) and linked scenario reports in that directory.
- Result: all 120 positive endpoint observations passed: native and polling watchers, three mutation modes, 20 rounds each. The disabled-watcher control correctly returned stale.
- Analysis: these are real Vite HTTP module-token checks from edits on guest-local Linux storage. They establish freshness at the tested endpoint; browser DOM application is checked separately. No runner repair was needed.
- Next verification: run the same repeated mutation combinations through actual Linux Chromium DOM/HMR observation.

## Cycle 47 Debian VM real Chromium HMR matrix

- Evidence: [summary](../evidence/matrices/debian-vm-chromium-hmr-2026-09-30/summary.json) and linked scenario reports in that directory.
- Result: all 120 positive DOM updates passed across native/polling watchers and all three mutation modes. Every scenario retained one page session and observed at least 20 HMR callbacks. The disabled-watcher control correctly remained stale with zero callbacks and retained its session.
- Analysis: actual Linux Chromium DOM state was observed in the provisioned Debian VMware guest. The fixture exercises dependency-accept HMR; other browser engines, application fixtures, and physical Linux hardware remain unverified. No repair was needed.
- Next verification: inspect process cleanup after these complete matrices, retrieve guest evidence, and audit artifact consistency and documentation links.

## Cycle 48 Debian process cleanup after matrices

- Evidence: [JSON](../evidence/test-runs/20260930T144950Z-debian-vm-matrix-cleanup-15ddc7.json), [console log](../evidence/test-runs/20260930T144950Z-debian-vm-matrix-cleanup-15ddc7.log).
- Result: the actual guest process check passed again after both repeated matrices; no live project-local Node/Chromium/crash-handler executable remained.
- Analysis: this checks cleanup after the larger real-tool experiments, in addition to the earlier full-suite check. Its scope is the observed project-local executable paths and completed runs.
- Next verification: retrieve retained guest artifacts, inspect recorded environment and per-round outcomes, update current results, and audit local links/JSON before committing.

## Cycle 49 Imported VM artifact audit

- Evidence: [JSON](../evidence/test-runs/20260930T145418Z-debian-vm-artifact-audit-f0d6af.json), [console log](../evidence/test-runs/20260930T145418Z-debian-vm-artifact-audit-f0d6af.log).
- Result: all three audit checks passed with zero failures/errors/skips: retained JSON and matrix summary consistency, document links, and user-home path redaction.
- Analysis: 42 guest artifacts were imported only after the evidence archive SHA-256 matched the guest value; existing differing evidence would have stopped import. Failed provisioning attempts remain distinguishable from successful software runs. A targeted scan found neither the supplied credential nor private connection address in evidence.
- Completion: the actual Debian VM suite, endpoint matrix, Chromium HMR matrix, stale controls, and post-run process checks meet this environment's verification plan. Windows support regression also passed. Current documentation records the observed VM version and separates physical-hardware, other-browser, and research-validation limits. No additional broad test cycle is needed for this completed scope.
- Final content review: retained APT console logs contain original prompt/progress whitespace. The existing raw-log whitespace policy is extended only to the Debian provisioning logs, preserving evidence formatting; source and documentation whitespace checks remain enabled.

## Cycle 50 Requested Windows repeat

- Evidence: [JSON](../evidence/test-runs/20260930T150202Z-requested-windows-repeat-b0c0ae.json), [console log](../evidence/test-runs/20260930T150202Z-requested-windows-repeat-b0c0ae.log).
- Result: all 24 tests passed with no skips, failures, or errors against commit c73827a.
- Analysis: this repeat began before the user narrowed the request to remaining coverage. No repair is needed. Further work targets additional installed browsers and Linux browser engines rather than repeating completed Chromium matrices.
- Next verification: test installed Windows Edge, inspect pinned Firefox/WebKit availability, then provision and exercise those engines where supported. Physical Linux hardware remains unavailable; do not substitute VM results for it.

## Cycle 51 Installed Windows Edge integration

- Evidence: [JSON](../evidence/test-runs/20260930T150402Z-windows-edge-integration-db3ad6.json), [console log](../evidence/test-runs/20260930T150402Z-windows-edge-integration-db3ad6.log).
- Result: both real Microsoft Edge DOM/HMR and disabled-watcher control tests passed, with no skips. Installed Edge reports 154.0.4258.37.
- Analysis: Edge is an additional browser on the Chromium engine, not a separate rendering engine. Added explicit Firefox/WebKit selection to the adapter while preserving Chromium defaults; selected engine/channel will be recorded by future matrices.
- Next verification: run Edge across every watcher/mutation combination, then verify Firefox/WebKit on Debian using the pinned Playwright browser manifest.

## Cycle 52 Windows Edge repeated HMR matrix

- Evidence: [summary](../evidence/matrices/windows-edge-hmr-remaining-2026-09-30/summary.json) and scenario reports in that directory.
- Result: all 120 positive DOM updates passed across native/polling watchers and three mutation modes. Each positive scenario retained its session and observed 20 callbacks. The disabled-watcher control correctly stayed stale with zero callbacks.
- Analysis: installed Microsoft Edge now has repeated real-browser coverage distinct from Chrome. The generalized adapter preserves the Chromium launch path and records the selected engine and channel. No repair was needed.
- Next verification: install pinned Firefox/WebKit binaries on the guest and exercise their real DOM paths with deliberately stale controls.

## Cycle 53 Default Chrome regression after engine selection

- Evidence: [JSON](../evidence/test-runs/20260930T151158Z-browser-engine-chrome-default-18e321.json), [console log](../evidence/test-runs/20260930T151158Z-browser-engine-chrome-default-18e321.log).
- Result: both actual default Chrome DOM/HMR and disabled-watcher tests passed without skips.
- Analysis: the adapter's new engine selection preserves the existing default Chrome path. This targeted regression addresses the changed launch integration; no broad repeat was needed.
- Next verification: complete guest Firefox/WebKit provisioning and test the new engine paths.

## Cycle 54 Firefox/WebKit binaries installed; libraries missing

- Evidence: [archive provenance](../evidence/remaining-browser-download-provenance.json), [installer result](../evidence/remaining-browser-install.json), [installer log](../evidence/remaining-browser-install.log).
- Result: pinned Firefox 153.0 revision 1538 and WebKit 26.5 revision 2336 were downloaded over HTTPS, transfer hashes verified, and installed by the normal Playwright installer. The temporary mirror was shut down. Installer exit 0 includes a host validation warning for missing shared libraries; no browser test pass is claimed.
- Analysis and next action: the observed library warning agrees with the dependency dry run (228 missing package dependencies). The guest has 14 GiB available. Source files and package/manual-mark baselines are backed up under ignored reports before the engine support overlay and dependency installation. Install the official Firefox/WebKit dependency set with the existing scoped IPv4 APT configuration, record changes, then verify actual launches and HMR.
- Limit: archive hashes establish identity to host HTTPS downloads, not publisher signatures. These are Playwright browser builds; WebKit results must not be labeled Safari.

## Cycle 55 Invalid engine selection before repair

- Evidence: [JSON](../evidence/test-runs/20260930T151712Z-browser-engine-invalid-before-341d1a.json), [console log](../evidence/test-runs/20260930T151712Z-browser-engine-invalid-before-341d1a.log).
- Result: the invalid-engine integration test failed on the inherited object key `toString`. A normal unknown engine was rejected correctly, but prototype lookup reached the launch path instead of the explicit unsupported-engine diagnostic.
- Analysis and repair: use a Map containing only the three allowed engine entries. This addresses one engine-selection boundary; retain the failed test evidence and rerun the targeted real Node integration before browser tests.

## Cycle 56 Invalid engine selection after repair

- Evidence: [JSON](../evidence/test-runs/20260930T151817Z-browser-engine-invalid-after-096bea.json), [console log](../evidence/test-runs/20260930T151817Z-browser-engine-invalid-after-096bea.log).
- Result: the targeted integration passed for both a normal unknown value and `toString`. Both remain inconclusive with the explicit unsupported-engine diagnostic.
- Analysis: explicit Map lookup fixes the observed prototype-key launch problem. Browser integrations must verify all supported engine paths after this repair; no unsupported value is treated as a watcher defect.

## Cycle 57 Additional browser dependency downloads failed

- Evidence: [result and package comparison](../evidence/remaining-browser-dependencies.json), [installation log](../evidence/remaining-browser-dependencies.log).
- Result: the official Firefox/WebKit dependency installer exited 1 after APT could not connect to package archive HTTP endpoints. No packages were added or changed relative to the fresh baseline.
- Analysis: this is provisioning failure, not an HMR test failure. The scoped IPv4 retry that previously worked was insufficient on this attempt. Keep the failure and original sources unchanged; probe actual failed archive URLs over HTTP and HTTPS before choosing a per-command HTTPS source override.

## Cycle 58 Network diagnostic URL parsing corrected

- Evidence: [invalid initial probe](../evidence/remaining-browser-network-probe-parse-before.json), [corrected archive probe](../evidence/remaining-browser-network-probe.json).
- Result: the initial ad hoc extraction matched the `.deb` prefix inside repository hostnames and produced invalid URLs. Its DNS errors cannot describe real repository reachability.
- Analysis and repair: require `.deb` to end the complete URL at whitespace/end of input; retain the incorrect diagnostic and probe actual package URLs again. The prepared HTTPS override is per-command and has not changed system sources.

## Cycle 59 HTTPS dependency retry left two archive failures

- Evidence: [corrected reachability probe](../evidence/remaining-browser-network-probe.json), [scoped source override](../evidence/remaining-browser-https-source-override.json), [retry result](../evidence/remaining-browser-dependencies-https.json), [retry log](../evidence/remaining-browser-dependencies-https.log).
- Result: the probe observed transient DNS failures for one archive and HTTP/HTTPS success for another. The HTTPS installer retry fetched 36.9 MB, but two package archives failed with timeout/read errors. Installation exited 1, with zero added packages or version changes.
- Analysis and recovery: cached successful downloads are retained. Obtain the exact two missing archives through the host, verify their SHA-256 against guest APT package metadata, then let the normal installer use the complete package cache. Preserve both failed attempts and use a new package baseline/result filename for the final retry. The system sources file remains unchanged by this per-command override.

## Cycle 60 Chrome integration after selector repair

- Evidence: [JSON](../evidence/test-runs/20260930T175643Z-browser-selector-chrome-repaired-5be44c.json), [console log](../evidence/test-runs/20260930T175643Z-browser-selector-chrome-repaired-5be44c.log).
- Result: all three targeted browser tests passed without skips: real Chrome DOM/HMR, disabled-watcher stale control, and unknown/prototype-key engine rejection.
- Analysis: supported Chromium launch behavior remains correct after the explicit allowlist repair. The full suite's historical 24-test count predates this added boundary test; this is the current three-test browser integration result.
- Next verification: finish guest dependency installation and run those same three tests on Firefox and WebKit before repeated matrices.

## Cycle 61 Firefox/WebKit dependencies installed from verified cache recovery

- Evidence: [APT archive metadata](../evidence/remaining-browser-apt-cache-provenance.json), [successful installer and package changes](../evidence/remaining-browser-dependencies-cache.json), [installer log](../evidence/remaining-browser-dependencies-cache.log), [adapter provenance](../evidence/remaining-browser-adapter-provenance.json).
- Result: both missing host downloads matched SHA-256 and sizes from guest APT metadata. The normal dependency installer completed with exit 0, adding 228 packages and changing zero existing package versions. The system sources SHA-256 still matches the pre-override value.
- Analysis: failed HTTP/HTTPS downloads are retained separately; the recovery completed the cache without bypassing package checks. Package/manual-mark baselines and previous adapter files remain in ignored reports for reviewed rollback. Source overlay archive integrity was checked before updating the adapter, cleanup inspector, and tests.
- Next verification: test actual Firefox and WebKit DOM/HMR, stale controls, invalid engine selection, repeated matrices, and post-run process cleanup. Installation alone does not establish browser correctness.

## Cycle 62 Actual Debian Firefox integration

- Evidence: [JSON](../evidence/test-runs/20260930T180027Z-debian-firefox-integration-b544f6.json), [console log](../evidence/test-runs/20260930T180027Z-debian-firefox-integration-b544f6.log).
- Result: all three tests passed without skips, failures, or errors: actual Firefox DOM/HMR without reload, disabled-watcher stale detection, and invalid engine rejection.
- Analysis: Firefox's separate engine launch path works in the provisioned Debian guest. This verifies the dependency-accept fixture; repeated mutation coverage and other applications are separate checks. No repair was needed.
- Next verification: run the corresponding WebKit integration, then repeated engine matrices.

## Cycle 63 Actual Debian WebKit integration

- Evidence: [JSON](../evidence/test-runs/20260930T180231Z-debian-webkit-integration-cf85dd.json), [console log](../evidence/test-runs/20260930T180231Z-debian-webkit-integration-cf85dd.log).
- Result: all three tests passed without skips, failures, or errors: actual Playwright WebKit DOM/HMR, disabled-watcher stale control, and invalid engine rejection.
- Analysis: WebKit's separate engine path works in this Debian guest. This describes Playwright WebKit 26.5 on Linux, not macOS/iOS Safari. No repair was needed.
- Next verification: run 20 rounds per watcher/mutation combination on Firefox, then WebKit, followed by Chromium integration and process cleanup after the package changes.

## Cycle 64 Debian Firefox repeated HMR matrix

- Evidence: [summary](../evidence/matrices/debian-firefox-hmr-2026-10-01/summary.json) and retained per-scenario reports.
- Result: all 120 positive DOM updates passed across native/polling watchers and three mutation modes. Every positive scenario retained one page session with 20 callbacks. The disabled-watcher control stayed stale with zero callbacks and preserved its session.
- Analysis: actual Firefox 153.0 on the Debian guest now has repeated dependency-accept HMR coverage, separate from Chromium. No repair was needed. Timing remains scenario policy rather than a cross-browser performance benchmark.
- Next verification: run the corresponding 120-update WebKit matrix and then inspect affected Chromium integration and all-engine process cleanup.

## Cycle 65 Debian WebKit repeated HMR matrix

- Evidence: [summary](../evidence/matrices/debian-webkit-hmr-2026-10-01/summary.json) and retained per-scenario reports.
- Result: all 120 positive DOM updates passed across native/polling watchers and three mutation modes. All positive scenarios retained one session and observed 20 callbacks. The disabled-watcher control stayed stale with zero callbacks and preserved its session.
- Analysis: actual Playwright WebKit 26.5 on Debian now has repeated dependency-accept HMR coverage. This is neither Safari testing nor a claim about every application. No repair was needed.
- Next verification: check the previously provisioned Linux Chromium path after the additional library installation and selector changes, then inspect process cleanup for all project-local engines.

## Cycle 66 Linux Chromium after engine and package updates

- Evidence: [JSON](../evidence/test-runs/20260930T180801Z-debian-chromium-after-engines-a7fc41.json), [console log](../evidence/test-runs/20260930T180801Z-debian-chromium-after-engines-a7fc41.log).
- Result: all three targeted integration tests passed without skips, failures, or errors: real Linux Chromium HMR, deliberately stale control, and invalid engine rejection.
- Analysis: the existing Linux Chromium path remains working after the changed selector and additional library installation. This targeted check addresses the affected integration; historical full-suite counts are preserved without claiming a new full-suite run.
- Next verification: inspect all live project-local executable paths after the completed Firefox/WebKit matrices and Chromium checks, then import and audit retained evidence.

## Cycle 67 Cleanup after all guest browser engines

- Evidence: [JSON](../evidence/test-runs/20260930T181025Z-debian-all-engine-cleanup-2f3562.json), [console log](../evidence/test-runs/20260930T181025Z-debian-all-engine-cleanup-2f3562.log).
- Result: the expanded actual /proc inspection passed with no live executable under project-local runtime/browser storage after Chromium, Firefox, and WebKit experiments.
- Analysis: this extends the former name-limited check to every project-local executable path, covering selected browser descendants without assuming their executable names. Its scope excludes external runtime paths and deliberately escaped processes. No cleanup repair was needed.
- Next verification: retrieve guest records, confirm per-round counts/versions and unchanged system sources, audit artifact consistency/local links/redaction, and commit reviewed changes.

## Cycle 68 Remaining browser artifact audit

- Evidence: [JSON](../evidence/test-runs/20260930T181438Z-remaining-browser-artifact-audit-9127c7.json), [console log](../evidence/test-runs/20260930T181438Z-remaining-browser-artifact-audit-9127c7.log).
- Result: all three audit checks passed without skips, failures, or errors: JSON and matrix-summary consistency, document links, and user-home redaction. A targeted scan found no supplied credential, private connection address, or literal guest user-home path in evidence.
- Analysis: 39 guest artifacts were imported after verifying the archive SHA-256; existing differing evidence would stop import. Original installation failures and the selector failure are retained alongside successful repairs. Edge, Firefox, and WebKit each passed 120 real DOM observations plus their correctly stale control; affected Chrome/Chromium integration and all-engine cleanup passed.
- Completion and limits: browser-engine coverage available on the Windows host and Debian VM is complete for this dependency-accept fixture. Physical Linux hardware and Safari on Apple devices require separate machines; application-specific fixtures require the actual application. No novelty or maintainer usefulness claim is established by these passes. Final source/document diff and whitespace checks are reviewed before local commit.

## Cycle 69 Current Windows readiness suite exposed startup failures

- Evidence: [JSON](../evidence/test-runs/20260930T184029Z-readiness-windows-full-3094c2.json), [console log](../evidence/test-runs/20260930T184029Z-readiness-windows-full-3094c2.log).
- Result: 25 tests ran; 22 passed and three failed, with no errors or skips. HTTP and disabled-watcher Vite checks never completed baseline readiness; the short stale-file fixture also failed baseline startup. Existing browser, cleanup, bounded-output, and decision tests passed.
- Analysis: HTTP workers are currently terminated on every 500 ms read-slice timeout, including process startup. Under slower startup this can repeatedly discard a worker before it returns anything. Confirm with a deliberately delayed worker before changing the probe. The stale-file fixture's 350 ms observation budget also doubles as its startup budget; queue that separate fixture issue after the HTTP repair.
- Readiness finding queued separately: `license = "MIT"` uses SPDX-expression metadata but the build requirement permits setuptools 61. Official setuptools documentation introduces that support at 77. Packaging/build and installed-CLI verification are missing release checks; address them after startup behavior is verified.

## Cycle 70 Delayed HTTP worker reproduces startup starvation

- Evidence: [JSON](../evidence/test-runs/20260930T184502Z-delayed-http-worker-before-9fb176.json), [console log](../evidence/test-runs/20260930T184502Z-delayed-http-worker-before-9fb176.log).
- Result: a real worker deliberately delayed by 650 ms failed to return within a 3-second scenario budget because every 500 ms slice restarted it.
- Analysis and repair: retain an outstanding request across read slices, use the enclosing observation deadline to cancel unfinished work, and reset on URL/body-limit changes. A worker's socket read must not impose a shorter hidden budget than the scenario. Add slow-header and changed-request checks alongside the existing slow-body/oversize cases; preserve process cleanup at the observation boundary.

## Cycle 71 HTTP repair exposed pending-sample stability handling

- Evidence: [JSON](../evidence/test-runs/20260930T185526Z-http-slice-budget-after-4f81df.json), [console log](../evidence/test-runs/20260930T185526Z-http-slice-budget-after-4f81df.log).
- Result: seven of eight targeted tests passed. Delayed startup, body limits, hard slow-body deadline, changed request, and decision checks passed; repeated slow-header responses still failed stability despite returning matching bytes.
- Analysis and follow-up: a pending read is not a completed unreadable observation. Distinguish `probe_pending` from request/deadline failures and preserve the previous match across pending slices, requiring another actual matching response before success. Add a controlled deadline check so a pending response can never pass merely from elapsed stable time. This completes the same HTTP slice/budget repair; other queued issues remain separate.

## Cycle 72 HTTP pending observations verified

- Evidence: [JSON](../evidence/test-runs/20260930T185828Z-http-pending-observation-after-30b2dd.json), [console log](../evidence/test-runs/20260930T185828Z-http-pending-observation-after-30b2dd.log).
- Result: all nine targeted checks passed, including deliberately delayed worker startup, slow headers, pending response after an earlier match, changed URL/body limit, oversized output, slow-body hard deadline, late match, exited process, and transient stale output.
- Analysis: pending slices retain the request without pretending to be new observations. A subsequent actual matching response is still required for success, and pending work is canceled at the overall observation boundary. The recorded starvation failure is resolved without relaxing the overall deadline or body limit.
- Next repair: give the stale-file test a separate startup budget while retaining its short observation budget, then check CLI report-write errors and package builds before final full suites.

## Cycle 73 Stale fixture startup policy repaired

- Evidence: [JSON](../evidence/test-runs/20260930T190349Z-stale-fixture-startup-after-58895e.json), [console log](../evidence/test-runs/20260930T190349Z-stale-fixture-startup-after-58895e.log).
- Result: the real stale-file integration passed after assigning a 3-second startup budget. Its mutation observation budget remains 350 ms.
- Analysis: the original failure occurred before baseline readiness, so it did not evaluate stale detection. Separating startup policy uses the already supported scenario field and preserves the original short mutation check; runner deadlines are unchanged.

## Cycle 74 CLI report destination failure confirmed

- Evidence: [JSON](../evidence/test-runs/20260930T190442Z-cli-report-error-before-5b8178.json), [console log](../evidence/test-runs/20260930T190442Z-cli-report-error-before-5b8178.log).
- Result: the CLI report-directory integration failed: an existing directory supplied as `--report` raised an uncaught write exception instead of a controlled CLI error.
- Analysis and repair: handle report creation/write OSError with a concise error and exit 2, consistent with invalid CLI input. This is a separate output-export issue; preserve the failed test and verify both configuration errors and report-write errors.

## Cycle 75 CLI error handling verified

- Evidence: [JSON](../evidence/test-runs/20260930T190528Z-cli-report-error-after-34a7ec.json), [console log](../evidence/test-runs/20260930T190528Z-cli-report-error-after-34a7ec.log).
- Result: both CLI boundary tests passed, covering report-directory errors and four invalid scenario cases, with exit 2 and no traceback.
- Analysis: report creation/write failures now produce a controlled error. Successful report export and installed console-entrypoint behavior are checked by the next package smoke integration; no blanket filesystem-write success is claimed.

## Cycle 76 Permitted build backend rejects license metadata

- Evidence: [JSON](../evidence/test-runs/20260930T190915Z-permitted-backend-build-before-7faa94.json), [console log](../evidence/test-runs/20260930T190915Z-permitted-backend-build-before-7faa94.log), [verified backend provenance](../evidence/build-backend-provenance.json).
- Result: setuptools 76.1.0, permitted by the current `>=61` requirement, failed the actual wheel build because `project.license = "MIT"` was not accepted by its schema.
- Analysis and repair: raise the build requirement to `setuptools>=77.0.3`, matching the SPDX support floor and [official packaging example](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/). Verify a build using precisely that minimum, inspect wheel license/module contents, install into a fresh venv, and run the installed console from outside the checkout, including slow HTTP and invalid input. No publication is part of this test.

## Cycle 77 Minimum backend build reached a test-capture encoding error

- Evidence: [JSON](../evidence/test-runs/20260930T191014Z-minimum-backend-wheel-after-3ba38c.json), [console log](../evidence/test-runs/20260930T191014Z-minimum-backend-wheel-after-3ba38c.log).
- Result: the minimum-backend wheel built, license/module checks passed, and installation completed, but the smoke check errored while decoding the installed module's Unicode path. Child UTF-8 output was read using the controller's Windows CP1252 default; no end-to-end package pass is claimed.
- Analysis and repair: explicitly use UTF-8 for all package-check child output and enable UTF-8 for the build child too. This is test-harness capture repair, separate from the verified metadata schema issue. Re-run the complete isolated packaging check before final suites.

## Cycle 78 Installed console HTTP check failed

- Evidence: [JSON](../evidence/test-runs/20260930T191233Z-isolated-wheel-console-after-f0b771.json), [console log](../evidence/test-runs/20260930T191233Z-isolated-wheel-console-after-f0b771.log).
- Result: wheel build, license/module inspection, isolated installation, module location, atomic file updates, and file report export passed. The installed HTTP console returned exit 1. Its stderr was empty; the initial assertion did not retain the JSON diagnostics emitted on stdout.
- Analysis and next action: include both child stdout and stderr in package-check failure details, then reproduce to retain the actual HTTP report before selecting a repair. No installed-HTTP success or root cause is claimed yet.

## Cycle 79 Installed HTTP diagnostics identify fixture shadowing

- Evidence: [JSON](../evidence/test-runs/20260930T191658Z-installed-http-console-diagnostic-4084f5.json), [console log](../evidence/test-runs/20260930T191658Z-installed-http-console-diagnostic-4084f5.log).
- Result: the retained report shows `process_exited_1` and `ModuleNotFoundError`: the smoke fixture was named `http.py`, shadowing Python's standard-library `http` package. The installed runner correctly marked the failed worker inconclusive and exited 1.
- Analysis and repair: rename only the fixture to `server_worker.py`; do not change the runner for a fixture import error. Repeat the complete isolated package check with its stdout diagnostics retained on any failure.

## Cycle 80 Installed package complete smoke check

- Evidence: [JSON](../evidence/test-runs/20260930T191902Z-installed-package-complete-df4c90.json), [console log](../evidence/test-runs/20260930T191902Z-installed-package-complete-df4c90.log).
- Result: the complete packaging integration passed with setuptools 77.0.3: wheel contents and MIT metadata, fresh venv installation, import from the installed package, console file mutations/report export, slow HTTP responses, and invalid input handling.
- Analysis: UTF-8 capture and the fixture import name are corrected. The installed console works outside the source checkout on Windows Python 3.12. This verifies the minimum build backend; it does not establish every supported Python version or Linux wheel installation. Next, verify the full source suites on Windows and Debian using a recorded source overlay.

## Cycle 81 Current Windows complete suite

- Evidence: [JSON](../evidence/test-runs/20260930T192901Z-readiness-windows-repaired-78db90.json), [console log](../evidence/test-runs/20260930T192901Z-readiness-windows-repaired-78db90.log).
- Result: all 30 tests passed, zero failures, errors or skips, on Windows Python 3.12.14. This includes real Vite/Chrome, stale controls, delayed HTTP startup/headers, deadline decisions, body bounds, CLI errors and ordinary process-descendant cleanup.
- Analysis: the three baseline failures from Cycle 69 no longer reproduce with the recorded fixes and explicit fixture startup policy. This full suite is current-source verification; prior matrices remain historical. Next verify the same source overlay on Debian and repeat a 20-round HTTP matrix to exercise request reuse across mutations.

## Cycle 82 Current Debian VMware complete suite

- Evidence: [JSON](../evidence/test-runs/20260930T193050Z-readiness-debian-full-c6c072.json), [console log](../evidence/test-runs/20260930T193050Z-readiness-debian-full-c6c072.log), [source overlay](../evidence/readiness-source-provenance.json).
- Result: all 30 tests passed, zero failures, errors or skips, on actual Debian 12.15 VMware Python 3.11.2, including provisioned Chromium, Vite and the new HTTP/CLI boundaries.
- Analysis: the nine overlay files were SHA-256 verified and previous files backed up under ignored `reports/readiness-before/` before deployment. The archive base is 43c6f57 plus the recorded overlay, not a claim of a clean Git checkout. No system provisioning changed this round. Next inspect live project-local runtime cleanup and repeated Windows HTTP requests across mutations. Linux installed-wheel behavior remains untested.

## Cycle 83 Debian readiness process cleanup

- Evidence: [JSON](../evidence/test-runs/20260930T193151Z-readiness-debian-cleanup-151fc2.json), [console log](../evidence/test-runs/20260930T193151Z-readiness-debian-cleanup-151fc2.log).
- Result: the actual post-suite process inspector passed; no live executable remained under the project's runtime/browser storage.
- Analysis: this is guest process inspection after all tests completed, separate from simulated containment and ordinary-descendant integration. It does not establish containment for deliberately detached or cross-OS processes. Next exercise repeated HTTP observations against the real Vite matrix.

## Cycle 84 Repeated real Vite HTTP observations after repair

- Evidence: [matrix summary](../evidence/matrices/windows-readiness-http-2026-10-01/summary.json) and its seven scenario reports.
- Result: Windows Vite native and polling each passed overwrite, atomic replace and burst for 20 rounds per combination: 120 positive freshness checks. The disabled-watcher control correctly returned stale.
- Analysis: this exercises the repaired HTTP worker across repeated mutation observations on Windows, where startup starvation was first observed. Results confirm the configured sampled freshness policy; they are not performance benchmarks or proof of continuous correctness. Debian's current full suite passed independently; historical WSL2 and additional-engine matrices were not rerun for this HTTP repair. Next audit evidence and readiness documentation, then preserve the reviewed source and results in Git.

## Cycle 85 Readiness artifact audit

- Evidence: [JSON](../evidence/test-runs/20260930T193842Z-readiness-artifact-audit-4d2039.json), [console log](../evidence/test-runs/20260930T193842Z-readiness-artifact-audit-4d2039.log).
- Result: all three checks passed for saved JSON/matrix summary consistency, local documentation links and literal user-home path redaction, including the imported Debian readiness results.
- Analysis: full suites, installed package smoke, repeated HTTP matrix and guest cleanup meet this review's completion checks. Actual source diffs and source-transfer hashes were reviewed; failed evidence is preserved. The readiness assessment qualifies a local experimental pilot and explicitly retains unverified runtime/platform/application and research limits. No publication or system provisioning was performed during this round.

### Final VM artifact synchronization (operational)

The committed README, documentation and evidence archive from 2c1b99c was transferred and verified against SHA-256 `edd72905f3b053ce413ea5ab3ef874d5ea04514998280e17aa1bf94db1540cc3`. Previous documentation was backed up under `reports/readiness-final-notes-before/`. The first write pass stopped with PermissionError on existing `evidence/debian-vm-apt-source-change.json`; its bytes had already matched the archive. Retrying by retaining byte-identical existing records wrote 36 remaining files and retained 253 identical files. A final hash comparison verified all 289 archive files. Source files and system provisioning were unchanged. This was an artifact transfer recovery, not another software test or freshness failure.

## Cycle 86 Development plan documentation audit

- Evidence: [JSON](../evidence/test-runs/20260930T200206Z-development-plan-links-c03a88.json), [console log](../evidence/test-runs/20260930T200206Z-development-plan-links-c03a88.log).
- Result: all three artifact checks passed after adding the practical development plan and linking its installed-package/workflow acceptance gates from README and the original experiment plan.
- Analysis: this checks documentation links and retained evidence consistency; no software behavior changed. The user subsequently authorized autonomous development/testing and GitHub upload on success. Work begins with CLI/config preflight and installed-package usability for Windows/Debian, while preserving the existing runtime and research limits until verified.

## Cycle 87 Shared scenario preflight and CLI compatibility

- Evidence: [JSON](../evidence/test-runs/20260930T200935Z-scenario-preflight-d22995.json), [console log](../evidence/test-runs/20260930T200935Z-scenario-preflight-d22995.log).
- Result: all 13 targeted tests passed: preflight, CLI boundaries and existing file/HTTP runner behavior.
- Analysis: validation is shared with execution and now rejects invalid late fields before workspace allocation. `--validate` returns JSON/exit 0 without running scenario/version commands or mutating fixtures; a sentinel CLI integration and mocked side-effect boundaries verify that promise. Runtime rechecks copied paths before mutation. Existing command invocation and freshness results remain compatible. Next deliver installed starters and scenario-specific diagnostics; no full release readiness is claimed by this targeted run.

## Cycle 88 Starter creation and independent file workflow

- Evidence: [JSON](../evidence/test-runs/20260930T201753Z-installed-starter-source-d104e3.json), [console log](../evidence/test-runs/20260930T201753Z-installed-starter-source-d104e3.log).
- Result: all five targeted tests passed. All three starter templates validate; generated file projects pass each mutation mode without accessing checkout example assets, preserve their original fixture, and reject an existing destination without overwriting it. Existing CLI boundaries still pass.
- Analysis: starters now use installed package resources with explicit setuptools package-data, including pinned Vite/Playwright manifests and lockfile. This source run does not yet prove resources are present in wheel/sdist; the isolated package gate will check actual artifacts. Next add dependency diagnostics and verify installed assets on both operating systems.

## Cycle 89 Scenario dependency diagnostics

- Evidence: [JSON](../evidence/test-runs/20260930T202144Z-dependency-diagnostics-d99867.json), [console log](../evidence/test-runs/20260930T202144Z-dependency-diagnostics-d99867.log).
- Result: all seven targeted diagnostics/preflight/CLI checks passed. File diagnostics report ready without executing the watched command; a missing executable and missing Vite/browser assets produce actionable failures.
- Analysis: `--doctor` checks configuration, executable and referenced assets, pinned starter dependencies, and uses a bounded launch/close probe for browser scenarios to detect missing binaries/libraries. It does not start Vite or mutate fixtures. Browser probe end-to-end and installed-package checks remain for the real-environment gate. Next protect report replacement and provide an optional readable summary while preserving default JSON.

## Cycle 90 Interrupted export truncates the previous report

- Evidence: [JSON](../evidence/test-runs/20260930T202332Z-report-write-interruption-before-e68bf8.json), [console log](../evidence/test-runs/20260930T202332Z-report-write-interruption-before-e68bf8.log).
- Result: the controlled filesystem fault failed as expected: an interrupted write after truncation left the previous report containing only five characters.
- Analysis and repair: current direct writes handle OSError but cannot preserve a prior report. Stage the UTF-8 export in a temporary file beside the destination, flush it, then replace only after completion. Verify active partial-write and replace-failure injections preserve the old bytes and remove temporary files; retain this original failure.

## Cycle 91 Report replacement and presentation recovery

- Evidence: [JSON](../evidence/test-runs/20260930T202528Z-report-export-recovery-8fdedb.json), [console log](../evidence/test-runs/20260930T202528Z-report-export-recovery-8fdedb.log).
- Result: all five export/CLI checks passed. Active partial-write and replace-failure injections preserve prior report bytes and leave no temporary files; successful summary output still saves JSON; default stdout JSON and freshness exit codes remain compatible.
- Analysis: UTF-8 export is staged beside the destination, flushed and replaced after completion. Fault assertions prove the simulated interruptions executed rather than being bypassed by the repair. `--format summary` is optional. Cancellation now returns 130 without a traceback after runner teardown, but actual signal/process verification remains outstanding. Next verify installed wheel/sdist assets and the real starter workflows.

## Cycle 92 Installed wheel, sdist and packaged starters

- Evidence: [JSON](../evidence/test-runs/20260930T202854Z-installed-wheel-sdist-starters-476058.json), [console log](../evidence/test-runs/20260930T202854Z-installed-wheel-sdist-starters-476058.log), [portable build provenance](../evidence/portable-build-toolchain.json).
- Result: the expanded installed-package integration passed with exact minimum setuptools 77.0.3. Wheel assets/license were inspected, sdist rebuilt to a wheel with identical package bytes, that wheel installed into a fresh venv, and all three starters created/validated outside checkout. Installed file diagnostics, summary, mutation/report and slow HTTP checks passed.
- Analysis: installed resources now have real distribution coverage on Windows. Verified pip/setuptools/wheel were also extracted into ignored guest project storage because system pip/setuptools were absent; system Python/packages were not changed. Their import versions were checked separately from software tests. Debian installed-package and full Vite/browser starter workflows remain next gates.

## Cycle 93 Debian installed wheel, sdist and starter workflow

- Evidence: [JSON](../evidence/test-runs/20260930T203413Z-debian-installed-wheel-sdist-e09bc7.json), [console log](../evidence/test-runs/20260930T203413Z-debian-installed-wheel-sdist-e09bc7.log), [deployed source hashes](../evidence/delivery-source-1898e8e.json).
- Result: the complete isolated package test passed on actual Debian Python 3.11.2: exact minimum backend, wheel/sdist rebuild, installed resources, all starter validations, file diagnostics/summary/report and slow HTTP console behavior.
- Analysis: the 69 source files from commit 1898e8e were checked against their transferred archive and changed files backed up before applying. Guest pip/build tools remained project-local and the fresh venv did not use checkout imports. This closes the previous Linux installed-package gap. Actual installed Vite/browser matrices and signal cancellation remain to be verified.

## Cycle 94 Configurable DOM and independent navigation identity

- Evidence: [JSON](../evidence/test-runs/20260930T203833Z-browser-selector-compatible-043659.json), [console log](../evidence/test-runs/20260930T203833Z-browser-selector-compatible-043659.log).
- Result: all three real Chrome/selector boundary integrations passed, including DOM updates and disabled-watcher control.
- Analysis: the browser adapter now accepts a DOM selector and creates its own per-document session, so normal applications need not expose the fixture's session marker. It distinguishes application callback metrics from sampled DOM-change counts. Existing fixture callback verification remains compatible. Next exercise the installed multi-module application with retained user state on each provisioned engine; this three-test run does not establish those new workflows.

## Cycle 95 Versioned package and multi-module starter distribution

- Evidence: [JSON](../evidence/test-runs/20260930T204359Z-release-package-generic-browser-b31826.json), [console log](../evidence/test-runs/20260930T204359Z-release-package-generic-browser-b31826.log).
- Result: all four package/starter checks passed after adding generic DOM selectors, optional interaction/retained-state checks and a multi-module application starter. Distribution rebuild and isolated file/HTTP checks still pass with version 1.0.0.
- Analysis: version now comes from one package constant; release artifacts were built once into ignored `reports/release-candidate-1.0.0` with package-source hashes and checksums. This is a candidate, not a published or accepted release. The installed application matrix must now prove DOM/session/state behavior with actual Vite and browsers before acceptance.

### Windows starter dependency setup (operational)

The first pnpm setup failed with EPERM when approved host-account commands tried to read files staged by the sandbox account. ACL inspection found non-inherited creator permissions on those staged files. Creating and installing new starter projects under one consistent Windows account succeeded, reusing all 16 pinned packages from the pnpm store. No global ACL or system package changes were made; the original failed setup directories remain in ignored reports. This setup failure is separate from watch freshness.

## Cycle 96 Installed Windows Vite HTTP application matrix

- Evidence: [JSON](../evidence/test-runs/20260930T204955Z-installed-windows-vite-http-64478d.json), [console log](../evidence/test-runs/20260930T204955Z-installed-windows-vite-http-64478d.log), [matrix](../evidence/matrices/installed-windows-vite-http-1.0.0/summary.json), [candidate identity](../evidence/release-candidate-1.0.0-manifest.json).
- Result: the installed candidate passed all 120 real Vite endpoint updates across native/polling and three mutation modes; the disabled watcher correctly returned stale/exit 1. Dependency diagnostics passed and original fixture bytes were retained.
- Analysis: actual installed code and generated starter assets were used; these are endpoint observations, not browser HMR evidence. After test completion, Git metadata capture emitted CP1252 reader-thread decode errors on the Thai checkout path; the recorder still saved the matrix/test result with unavailable metadata. Preserve this result and repair UTF-8 Git capture through a controlled real Git-path check before subsequent gates.

## Cycle 97 Git-path encoding failure confirmed

- Evidence: [JSON](../evidence/test-runs/20260930T205314Z-git-path-encoding-before-a81f63.json), [console log](../evidence/test-runs/20260930T205314Z-git-path-encoding-before-a81f63.log).
- Result: the actual Unicode checkout-path capture errored: UTF-8 Git output could not be decoded by CP1252, leaving stdout unavailable.
- Analysis and repair: decode Git output as UTF-8, bound metadata capture time and trust only the known recorder project through a per-command safe.directory. The regression will use its own temporary Unicode Git repository, so archive-based guest execution does not depend on the source directory having .git. Preserve this controller failure separately from installed CLI freshness results.

## Cycle 98 UTF-8 Git recording verified

- Evidence: [JSON](../evidence/test-runs/20260930T205437Z-git-path-encoding-after-543e46.json), [console log](../evidence/test-runs/20260930T205437Z-git-path-encoding-after-543e46.log).
- Result: all three recorder checks passed, including real Git output from a temporary Unicode repository and missing-Git handling; metadata capture completed without reader-thread decoding errors.
- Analysis: Git capture now uses explicit UTF-8, a five-second bound, and project-scoped per-command trust. No global Git configuration changed. The installed candidate's package bytes are unaffected by this test-controller repair. Continue real installed browser/guest matrices and cancellation verification before release gates.

## Cycle 99 Installed Windows Chrome application and retained state

- Evidence: [JSON](../evidence/test-runs/20260930T205540Z-installed-windows-chrome-d08ca5.json), [console log](../evidence/test-runs/20260930T205540Z-installed-windows-chrome-d08ca5.log), [matrix](../evidence/matrices/installed-windows-chrome-1.0.0/summary.json).
- Result: installed candidate diagnostics and all 120 DOM updates passed across native/polling and three mutation modes. Each scenario retained its independent page session and the counter state set by a real button click; disabled watching correctly produced stale with zero updates.
- Analysis: this multi-module vanilla Vite application uses a configurable DOM selector and no fixture-owned session/HMR globals. Its update metric is sampled DOM changes, not framework callback counts. Original fixture bytes stayed unchanged. This verifies the selected installed application workflow on Chrome; other frameworks and engines require their own evidence.

## Cycle 100 Debian installed workflow harness dereferenced the venv

- Evidence: [JSON](../evidence/test-runs/20260930T205746Z-installed-debian-vite-http-fce658.json), [console log](../evidence/test-runs/20260930T205746Z-installed-debian-vite-http-fce658.log), [doctor diagnostic](../evidence/matrices/installed-debian-vite-http-1.0.0/doctor.json).
- Result: the installed matrix stopped before Vite launch: the harness resolved the venv Python symlink to the system interpreter, which correctly had no installed package.
- Analysis and repair: preserve the venv launcher path with absolute(), without resolving its target. The product wheel and earlier genuine venv package integration are unchanged; this is a test-controller error, not a Linux package import failure. Retain the failed directory, back up the guest harness and rerun into a new evidence directory.

## Cycle 101 Installed Debian Vite HTTP matrix after harness repair

- Evidence: [JSON](../evidence/test-runs/20260930T205925Z-installed-debian-vite-http-repaired-4b3a93.json), [console log](../evidence/test-runs/20260930T205925Z-installed-debian-vite-http-repaired-4b3a93.log), [matrix](../evidence/matrices/installed-debian-vite-http-repaired-1.0.0/summary.json), [harness repair hashes](../evidence/delivery-harness-repair.json).
- Result: the same verified candidate wheel passed dependency diagnostics, all 120 endpoint updates across watcher/mutation combinations, and the expected-stale disabled control. Original fixture bytes were retained.
- Analysis: preserving the venv executable path resolved the controller error. Guest and host repaired harness SHA-256 values agree; the wheel bytes were unchanged. This is actual installed Debian/Vite verification. Continue the installed browser engines and real-process cancellation checks.

## Cycle 102 Installed Windows cancellation and cleanup

- Evidence: [JSON](../evidence/test-runs/20260930T210320Z-installed-windows-sigint-9561f4.json), [console log](../evidence/test-runs/20260930T210320Z-installed-windows-sigint-9561f4.log).
- Result: both file-baseline and pending-HTTP subcases passed in a real installed CLI subprocess: a controlled in-process SIGINT returned 130, produced no traceback and stopped the watched process, its ordinary descendant and the pending HTTP worker.
- Analysis: this exercises real signal handling and process cleanup, with a controlled self-delivered SIGINT rather than a physical console keypress. No product bytes changed. Next verify guest cancellation and all installed browser engines, then validate release CI and user documentation.

## Cycle 103 Installed Debian cancellation and cleanup

- Evidence: [JSON](../evidence/test-runs/20260930T210538Z-installed-debian-sigint-af2488.json), [console log](../evidence/test-runs/20260930T210538Z-installed-debian-sigint-af2488.log).
- Result: both real-process file-baseline and pending-HTTP SIGINT subcases passed on the installed candidate, with exit 130, no traceback and no surviving watch/descendant/probe process.
- Analysis: host and guest now have verified controlled signal teardown for installed code. The Linux harness retains the venv symlink path; no product bytes were changed. Next run installed Chromium/Firefox/WebKit and Edge stateful workflows, then final source and artifact gates.

## Cycle 104 Debian browser state gate caught source-shadowed starter creation

- Evidence: [JSON](../evidence/test-runs/20260930T211013Z-installed-debian-chromium-b7650a.json), [console log](../evidence/test-runs/20260930T211013Z-installed-debian-chromium-b7650a.log), [first scenario](../evidence/matrices/installed-debian-chromium-1.0.0/scenario-overwrite.json).
- Result: dependency diagnostics and 20 DOM token updates passed, but the application-state gate correctly failed: the generated project had the older fixture/adapter and no retained-state metric.
- Analysis and correction: setup invoked the venv with cwd at the source checkout, allowing `-m watchmode_truth_lab --init` to import checkout code. The actual matrix subprocess used installed code from the generated directory, but starter creation was not isolated. Earlier Windows checkout code matched candidate bytes, while Debian's older checkout exposed the setup error. Preserve those results as installed-runtime checks with source-created assets; they do not prove end-to-end installed starter creation. Create fresh projects from an independent cwd, assert installed module location, and fix CI setup before repeating the affected matrices. Product wheel bytes remain unchanged.

## Cycle 105 Installed Windows Edge with source-created matching assets

- Evidence: [JSON](../evidence/test-runs/20260930T211020Z-installed-windows-edge-db1d8c.json), [console log](../evidence/test-runs/20260930T211020Z-installed-windows-edge-db1d8c.log), [matrix](../evidence/matrices/installed-windows-edge-1.0.0/summary.json).
- Result: all 120 DOM updates passed, with independent page session, retained counter state and the expected-stale disabled control.
- Analysis: actual runtime was the installed candidate. Cycle 104 identified that setup generated its matching assets through the checkout rather than the installed package, so this matrix is retained but not used as the final installed-creation acceptance gate. Repeat from starters created under a clean cwd and verified installed module location. No watch/HMR defect was observed.

## Cycle 106 Clean-cwd installed Debian Chromium workflow

- Evidence: [JSON](../evidence/test-runs/20260930T211707Z-installed-debian-chromium-clean-init-eff214.json), [console log](../evidence/test-runs/20260930T211707Z-installed-debian-chromium-clean-init-eff214.log), [matrix](../evidence/matrices/installed-debian-chromium-clean-init-1.0.0/summary.json).
- Result: all 120 DOM updates passed, preserving per-document session and clicked counter state; disabled watching correctly stayed stale with zero updates. Diagnostics and fixture preservation passed.
- Analysis: new projects were created from the installed wheel under an independent cwd after asserting imported module location within the venv. Pinned dependencies were installed offline from cache. This resolves the setup-shadowing failure; source-shadowed project directories and failed evidence remain intact. These are real Debian Chromium observations of sampled DOM changes, not application callback counts.

## Cycle 107 Clean-cwd installed Windows HTTP workflow

- Evidence: [JSON](../evidence/test-runs/20260930T211715Z-installed-windows-http-clean-init-6a32c7.json), [console log](../evidence/test-runs/20260930T211715Z-installed-windows-http-clean-init-6a32c7.log), [matrix](../evidence/matrices/installed-windows-http-clean-init-1.0.0/summary.json).
- Result: all 120 real Vite HTTP updates passed across native/polling and three mutation modes; stale control/exit 1, diagnostics and original fixture retention passed.
- Analysis: creation and execution now both use installed package code, with the import location checked before setup. This replaces the earlier source-created-assets result as the installed HTTP acceptance gate. Same-account setup avoids Windows ACL context changes. Continue the other browser engines and release gates.

## Cycle 108 Clean-cwd installed Debian Firefox workflow

- Evidence: [JSON](../evidence/test-runs/20260930T212117Z-installed-debian-firefox-clean-init-af7c47.json), [console log](../evidence/test-runs/20260930T212117Z-installed-debian-firefox-clean-init-af7c47.log), [matrix](../evidence/matrices/installed-debian-firefox-clean-init-1.0.0/summary.json).
- Result: all 120 native/polling DOM updates passed with retained clicked state and independent page session; disabled watching correctly stayed stale with zero updates.
- Analysis: this is the actual provisioned Firefox engine with installed starter creation/execution and pinned dependencies, not an inference from Chromium. Diagnostics and original fixture preservation also passed. Continue WebKit and the remaining clean-creation host/guest gates.

## Cycle 109 Clean-cwd installed Windows Chrome workflow

- Evidence: [JSON](../evidence/test-runs/20260930T212124Z-installed-windows-chrome-clean-init-f015f2.json), [console log](../evidence/test-runs/20260930T212124Z-installed-windows-chrome-clean-init-f015f2.log), [matrix](../evidence/matrices/installed-windows-chrome-clean-init-1.0.0/summary.json).
- Result: all 120 DOM updates passed with retained clicked state and page session; the disabled watcher correctly returned stale/exit 1. Diagnostics and fixture preservation passed.
- Analysis: this repeat resolves the setup-shadowing risk identified in Cycle 104: creation and execution both used the installed package from independent cwd locations. The source-created-assets matrix remains historical and is not substituted for this acceptance evidence.

## Cycle 110 Clean-cwd installed Debian WebKit workflow

- Evidence: [JSON](../evidence/test-runs/20260930T212520Z-installed-debian-webkit-clean-init-0ff4cc.json), [console log](../evidence/test-runs/20260930T212520Z-installed-debian-webkit-clean-init-0ff4cc.log), [matrix](../evidence/matrices/installed-debian-webkit-clean-init-1.0.0/summary.json).
- Result: all 120 DOM updates passed with independent document identity and retained clicked counter state. Diagnostics, original fixture preservation and the expected-stale disabled control passed.
- Analysis: this is installed-package creation and execution on the provisioned Debian WebKit engine, not Safari or physical hardware. The earlier source-created assets are not used as this acceptance gate. No product changes were needed.

## Cycle 111 Clean-cwd installed Windows Edge workflow

- Evidence: [JSON](../evidence/test-runs/20260930T212526Z-installed-windows-edge-clean-init-62be3d.json), [console log](../evidence/test-runs/20260930T212526Z-installed-windows-edge-clean-init-62be3d.log), [matrix](../evidence/matrices/installed-windows-edge-clean-init-1.0.0/summary.json).
- Result: all 120 DOM updates passed, preserving document identity and clicked application state; diagnostics, fixture retention and expected-stale/exit 1 passed.
- Analysis: clean-cwd installed creation closes the Windows setup-shadowing qualification. The selected Chrome, Edge, Debian Chromium, Firefox and WebKit engines now have installed stateful application evidence. Complete the clean Debian HTTP repeat and final source/package/CI gates before publication.

## Cycle 112 Clean-cwd installed Debian HTTP workflow

- Evidence: [JSON](../evidence/test-runs/20260930T213503Z-installed-debian-http-clean-init-a08560.json), [console log](../evidence/test-runs/20260930T213503Z-installed-debian-http-clean-init-a08560.log), [matrix](../evidence/matrices/installed-debian-http-clean-init-1.0.0/summary.json).
- Result: all 120 HTTP updates and the expected-stale control passed with installed creation and execution, ready diagnostics and unchanged original fixture bytes.
- Analysis: this closes the earlier source-created-assets qualification for Debian HTTP. The candidate has actual installed HTTP and stateful DOM verification on Windows and Debian. These are the provisioned VM and selected applications; final source/CI gates remain.

## Cycle 113 Dependency diagnostic boundary failures reproduced

- Evidence: [JSON](../evidence/test-runs/20260930T213545Z-doctor-metadata-before-d648cb.json), [console log](../evidence/test-runs/20260930T213545Z-doctor-metadata-before-d648cb.log).
- Result: six tests ran; new controlled metadata cases produced two failed assertions and three AttributeErrors. Both new CI analysis gate tests passed, rejecting skipped/empty/failed/wrong-revision records.
- Analysis and repair: doctor assumes package.json and devDependencies are objects, assumes installed package metadata is an object, and mistakes digit-leading ranges for exact pins. Validate these shapes and dependency names/specifications; produce actionable not_ready checks on malformed metadata and explicitly qualify unverified range compatibility. The principal repair is dependency diagnosis. Previously accepted runner/browser behavior and artifacts remain unchanged until a new package is built.

## Cycle 114 Dependency diagnostics recovery and CI gate analysis

- Evidence: [JSON](../evidence/test-runs/20260930T213651Z-doctor-metadata-after-9188b0.json), [console log](../evidence/test-runs/20260930T213651Z-doctor-metadata-after-9188b0.log).
- Result: all nine diagnostics, starter and CI gate tests passed without skips. Invalid metadata returns structured not_ready checks; digit-leading ranges are explicitly labeled as unverified compatibility rather than exact-pin mismatches.
- Analysis: this repairs the confirmed dependency-diagnosis boundary while retaining strict equality for the pinned starter dependencies. Range presence is not dependency resolution. Product diagnostics changed, so build a new candidate and verify its installed diagnostics/package workflows; earlier engine evidence still describes the unchanged runner and adapter bytes.

## Cycle 115 Complete Windows release-source regression

- Evidence: [JSON](../evidence/test-runs/20260930T213742Z-release-source-windows-8e0ef0.json), [console log](../evidence/test-runs/20260930T213742Z-release-source-windows-8e0ef0.log).
- Result: all 46 tests passed, zero failures/errors/skips, including actual Chrome/Vite, stale controls and the repaired diagnostic boundary.
- Analysis: source regression covers current CLI, starters, report recovery, HTTP scheduling and browser adapter compatibility. This is source execution, distinct from installed candidate acceptance. Next verify the minimum-backend rebuilt sdist/installed version contract and deploy this current source to Debian with provenance and backups.

## Cycle 116 Final package rebuild and installed version contract

- Evidence: [JSON](../evidence/test-runs/20260930T213904Z-release-package-final-a28050.json), [console log](../evidence/test-runs/20260930T213904Z-release-package-final-a28050.log), [final artifact manifest](../evidence/release-final-1.0.0-manifest.json).
- Result: minimum-backend wheel/sdist rebuild integration passed, including clean installed imports, all three starters, CLI/module/distribution version agreement, file/report, slow HTTP and invalid-input handling.
- Analysis: the final candidate contains the corrected dependency diagnostics. Its runner/browser assets match the previously tested candidate; final installed Windows/Debian verification and remote CI are still required. Build outputs have immutable SHA-256 identities; keep earlier candidate and failed evidence.

## Cycle 117 Precommit artifact audit

- Evidence: [JSON](../evidence/test-runs/20260930T214034Z-release-artifacts-precommit-64262f.json), [console log](../evidence/test-runs/20260930T214034Z-release-artifacts-precommit-64262f.log).
- Result: all three checks passed for retained JSON/matrix agreement, local documentation links and literal home-path redaction, including the imported Debian installed matrices and their failures.
- Analysis: evidence import verified the archive SHA-256 and retained identical existing files without overwriting history. This audit checks retained content, not runtime correctness. Commit the reviewed source before the final backed-up guest deployment and actual remote CI.

## Cycle 118 Complete Debian release-source regression

- Evidence: [JSON](../evidence/test-runs/20260930T214327Z-release-source-debian-e2029d.json), [console log](../evidence/test-runs/20260930T214327Z-release-source-debian-e2029d.log), [deployment provenance](../evidence/release-source-debian-provenance.json).
- Result: all 46 tests passed with zero failures/errors/skips, including real Debian Chromium/Vite and current diagnostics, starter, report and process boundaries.
- Analysis: revision 06a0405 was deployed only after archive SHA-256/path validation and a backup of changed guest files. No system dependency changes were made. Git exports use LF while Windows working copies may use CRLF; executed-file hashes identify each copy. This source gate is separate from installing the exact final wheel and its upcoming matrices.

## Cycle 119 Exact final wheel Windows HTTP acceptance

- Evidence: [JSON](../evidence/test-runs/20260930T214429Z-final-installed-windows-http-6ad280.json), [console log](../evidence/test-runs/20260930T214429Z-final-installed-windows-http-6ad280.log), [matrix](../evidence/matrices/final-windows-http-1.0.0/summary.json), [artifact identity](../evidence/release-final-1.0.0-manifest.json).
- Result: final wheel installation into a new venv, independently created HTTP starter, dependency diagnostics, all 120 native/polling updates, unchanged fixture and expected-stale control passed.
- Analysis: this uses the exact final artifact, including the diagnostics repair, under one consistent Windows account and clean cwd. The candidate's HTTP workflow is accepted here. Continue its browser and guest installed gates; earlier engine evidence identifies the unchanged adapter.

## Cycle 120 Debian minimum-backend installed package contract

- Evidence: [JSON](../evidence/test-runs/20260930T214511Z-release-package-debian-643e08.json), [console log](../evidence/test-runs/20260930T214511Z-release-package-debian-643e08.log).
- Result: wheel/sdist rebuild integration passed with the exact minimum backend, all installed starters, outside-checkout imports, CLI/module/distribution version agreement, file/report, slow HTTP and controlled invalid input.
- Analysis: uses project-local build tools with no guest system Python changes. This closes the former Linux installed-package gap for the current source. Install the final Windows-built wheel after transfer SHA verification to prove the artifact supplied to users across both operating systems.

## Cycle 121 Exact final wheel Windows browser acceptance

- Evidence: [JSON](../evidence/test-runs/20260930T214550Z-final-installed-windows-browser-310ebf.json), [console log](../evidence/test-runs/20260930T214550Z-final-installed-windows-browser-310ebf.log), [matrix](../evidence/matrices/final-windows-chrome-1.0.0/summary.json).
- Result: all 120 DOM updates passed with retained clicked counter state and independent document identity; diagnostics, original fixture and expected-stale control passed.
- Analysis: a new venv and starter created outside the checkout exercised the exact final wheel. Earlier Edge and guest alternate-engine matrices used the identical browser/runner assets, with the earlier diagnostics implementation explicitly identified. No runtime adapter changes followed those engine checks.

## Cycle 122 Current WSL2 source compatibility

- Evidence: [JSON](../evidence/test-runs/20260930T214613Z-final-linux-wsl2-2f9957.json), [console log](../evidence/test-runs/20260930T214613Z-final-linux-wsl2-2f9957.log).
- Result: 46 collected tests, 43 passed and three browser tests explicitly skipped because this WSL2 lab has no provisioned browser. No failures or errors.
- Analysis: Linux-side WSL2 source execution covers current CLI/file/HTTP and failure boundaries with the existing pinned Node toolchain. Browser skips are not counted as verified browser behavior or required CI completion. Windows and Debian browser gates have no skips. Historical cross-origin mounted-storage native/polling findings remain separate and were not reinterpreted by this source repeat.

## Cycle 123 Exact final wheel Windows cancellation

- Evidence: [JSON](../evidence/test-runs/20260930T214746Z-final-installed-windows-cancel-3674ed.json), [console log](../evidence/test-runs/20260930T214746Z-final-installed-windows-cancel-3674ed.log).
- Result: installed real-process controlled SIGINT passed in both file-baseline/startup and pending-HTTP subcases, returning 130 without a traceback and leaving no watched process, ordinary descendant or pending worker alive.
- Analysis: confirms teardown for the exact final artifact; delivery was a controlled in-process signal, not a physical Ctrl+C console event. The runner bytes are unchanged from earlier guest cancellation verification. Keep this distinction in the user guide and release support claims.

## Cycle 124 Exact final wheel Debian HTTP acceptance

- Evidence: [JSON](../evidence/test-runs/20260930T214756Z-final-installed-debian-http-fd17c8.json), [console log](../evidence/test-runs/20260930T214756Z-final-installed-debian-http-fd17c8.log), [matrix](../evidence/matrices/final-debian-http-1.0.0/summary.json), [install identity](../evidence/final-debian-wheel-install.json).
- Result: transfer SHA-256 matched the final wheel; new venv/import location/independent starter creation passed. All 120 HTTP updates, diagnostics, unchanged fixture and the stale control passed.
- Analysis: Windows and Debian now exercise the exact same final wheel bytes for installed HTTP. Guest build tools/dependencies remain project-local and were reused without system changes. Continue its real browser, cancellation and cleanup gates.

## Cycle 125 Windows mutation cancellation responsiveness failed

- Evidence: [JSON](../evidence/test-runs/20260930T215005Z-installed-cancel-mutation-windows-8b14c5.json), [console log](../evidence/test-runs/20260930T215005Z-installed-cancel-mutation-windows-8b14c5.log).
- Result: startup and pending-HTTP subcases passed, but interruption during a 30-second external mutation exceeded the 20-second controller deadline.
- Analysis and repair: Windows process.wait(timeout=30) can leave a self-delivered SIGINT pending while waiting for the process handle. Poll captured-command completion in bounded short slices while preserving the original whole-command deadline, so version/mutation/browser diagnostics can return to Python signal handling promptly. This is a confirmed Windows cancellation responsiveness issue for controlled signals; no physical-console signal claim is made. Preserve the failed package and rebuild before accepting a release. Controller timeout killed only its launcher; inspect and clean only identified test-owned processes and improve failure cleanup.

## Cycle 126 Exact first final-wheel Debian browser acceptance

- Evidence: [JSON](../evidence/test-runs/20260930T214957Z-final-installed-debian-browser-3cd0df.json), [console log](../evidence/test-runs/20260930T214957Z-final-installed-debian-browser-3cd0df.log), [matrix](../evidence/matrices/final-debian-chromium-1.0.0/summary.json).
- Result: 120 DOM updates, retained state/session, ready diagnostics, original fixture and expected-stale control passed.
- Analysis: these identify the first final wheel; Cycle 125 found a separate captured-command cancellation issue, so this artifact is superseded for release acceptance. Browser adapter bytes need no repair, but the changed runner must receive final regression/installed gates.

## Cycle 127 Windows external-mutation cancellation repaired

- Evidence: [JSON](../evidence/test-runs/20260930T215300Z-installed-cancel-mutation-repaired-85bba3.json), [console log](../evidence/test-runs/20260930T215300Z-installed-cancel-mutation-repaired-85bba3.log), [rebuilt artifact identity](../evidence/release-1.0.0-r2-manifest.json).
- Result: startup, pending HTTP and external-mutation subcases passed with exit 130, no traceback and no live watch/mutator/ordinary descendant/probe. The previous failed fixture had no remaining matching owned Python process at inspection.
- Analysis: captured waits now return to Python in at most 100 ms slices while preserving their total deadline and cleanup. Failure cleanup in the controller is scoped to PIDs published by its own fixture. No global process termination was used. Complete live-browser cancellation and whole-source/installed regression for this revised artifact before publication.

## Cycle 128 Installed Windows live-browser cancellation

- Evidence: [JSON](../evidence/test-runs/20260930T215430Z-installed-browser-cancel-windows-993007.json), [console log](../evidence/test-runs/20260930T215430Z-installed-browser-cancel-windows-993007.log).
- Result: actual browser DOM observation became available, then controlled SIGINT returned 130 without a traceback; all observed adapter/Vite/browser descendant PIDs stopped.
- Analysis: the test records only process IDs/parent IDs from the installed CLI's own tree and verifies they are gone after normal cancellation. It deliberately keeps baseline observation pending after browser readiness to exercise live browser teardown. This is genuine installed browser/process integration with a self-delivered signal, not physical keyboard verification. Add it to required CI alongside mutation cancellation.

## Cycle 129 Complete revised Windows source regression

- Evidence: [JSON](../evidence/test-runs/20260930T215533Z-release-r2-source-windows-84113d.json), [console log](../evidence/test-runs/20260930T215533Z-release-r2-source-windows-84113d.log).
- Result: all 46 tests passed with no skips/failures/errors after the captured-command polling repair, including real Chrome/Vite and command timeout/noisy/failure cases.
- Analysis: the principal runner change retains bounded timeout and output behavior and passed the new installed mutation/browser interruption gates. Deploy revision bd3116c with backup/checksums to Debian, verify its source and installed cancellation, then upload the reviewed project to the existing private GitHub repository and observe required CI.

## Cycle 130 Complete revised Debian source regression

- Evidence: [JSON](../evidence/test-runs/20260930T215740Z-release-r2-source-debian-6cfaf8.json), [console log](../evidence/test-runs/20260930T215740Z-release-r2-source-debian-6cfaf8.log), [overlay provenance](../evidence/release-r2-debian-provenance.json).
- Result: all 46 tests passed without skips/failures/errors after the backed-up lifecycle overlay and exact r2 wheel installation.
- Analysis: current source behavior is verified on both operating systems, including timed-out version/mutator capture and real Chromium. Installed cancellation and browser matrix follow separately. No guest system packages changed.

## Cycle 131 Revised wheel Windows HTTP matrix

- Evidence: [JSON](../evidence/test-runs/20260930T215746Z-release-r2-windows-http-626286.json), [console log](../evidence/test-runs/20260930T215746Z-release-r2-windows-http-626286.log), [matrix](../evidence/matrices/release-r2-windows-http-1.0.0/summary.json).
- Result: all 120 HTTP updates passed after captured-wait repair; diagnostics, fixture preservation and expected-stale control passed.
- Analysis: verifies repeated installed HTTP behavior for r2. Browser adapter bytes are unchanged, while the new source and cancellation checks verify runner lifecycle effects. An independently observed report-reproduction quoting gap for special scenario filenames is queued for its own repair round before final CI.

## Cycle 132 Reproduction argument metadata boundary

- Evidence: [JSON](../evidence/test-runs/20260930T220000Z-reproduction-filename-before-bb8186.json), [console log](../evidence/test-runs/20260930T220000Z-reproduction-filename-before-bb8186.log).
- Result: a real successful scenario with spaces, apostrophe, dollar sign and Unicode in its filename produced a report, but the regression errored because structured reproduction argv was absent. The test did not yet execute the legacy shell string.
- Analysis and repair: code inspection shows the legacy cli interpolates the filename without quoting and assumes a python alias. Add structured argv using the current interpreter and a shell-labeled, quoted presentation for PowerShell/POSIX. Preserve schema 1 and existing fields. Verify actual shell execution from the scenario cwd after the repair rather than claiming the old string was experimentally executed.

## Cycle 133 Revised installed Debian cancellation gates

- Evidence: [JSON](../evidence/test-runs/20260930T215955Z-release-r2-debian-cancel-a61a5a.json), [console log](../evidence/test-runs/20260930T215955Z-release-r2-debian-cancel-a61a5a.log).
- Result: both tests passed without skips: startup/pending-HTTP/external-mutation controlled SIGINT with ordinary descendants, and actual live-browser cancellation with observed tree cleanup.
- Analysis: r2's lifecycle repair is verified on Windows and Debian; the report quoting repair is separate and does not change those process mechanisms. Guest signal evidence remains controlled in-process delivery, not keyboard input or detached process containment.

## Cycle 134 Special-filename reproduction and report compatibility

- Evidence: [JSON](../evidence/test-runs/20260930T220119Z-reproduction-filename-after-ac56b2.json), [console log](../evidence/test-runs/20260930T220119Z-reproduction-filename-after-ac56b2.log).
- Result: all six checks passed, including actually executing the report's PowerShell invocation with spaces/apostrophe/dollar sign/Unicode in the filename, preserving the selected interpreter and scenario arguments. Existing CLI/export checks passed.
- Analysis: structured argv and shell labels are additive schema 1 fields. Quoted presentation is platform-specific and still requires original cwd/dependencies/environment. Add installed argv execution to package verification and POSIX reproduction to Debian/required CI; preserve earlier failed metadata evidence.
