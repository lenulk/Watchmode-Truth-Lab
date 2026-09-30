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
- Other browser engines and application-specific HMR fixtures are not covered.
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
