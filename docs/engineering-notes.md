# Engineering notes

## Windows process cleanup and console encoding

The first toy-worker test run passed but emitted `ResourceWarning` because a killed process was not waited for. The runner now waits after termination. A CLI run also failed when a Thai workspace path was printed through a CP1252 console; the CLI configures UTF-8 output where supported.

Later tests exposed descendants surviving an exited launcher. Windows now establishes a guardian Job Object before starting commands; closing its final handle kills ordinary descendants. Linux terminates the process group even when its launcher has exited. Real regressions pass on Windows and Linux within WSL2. Deliberately detached processes and cross-OS process escape remain outside containment. See cycles 7–11 in [the test log](test-log.md) and [Microsoft's Job Object documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Vite adapter installation

The host `npm` command looked for a missing global npm CLI and could not install dependencies. The bundled pnpm CLI installed the pinned Vite version and wrote `pnpm-lock.yaml`. The first sandboxed pnpm attempt could not access the package registry; the approved network retry completed. This is an environment setup issue, not a watch-mode failure.

## WSL2 tool availability

Kali Linux is installed as a WSL2 distro with Python 3.13.12. Initially Node and pnpm were absent. `scripts/wsl_vite_lab.py` now provisions Linux Node 24.18.0 and pnpm 11.19.0 in a temporary lab, verifies the official Node archive checksum, and installs from the project's frozen lockfile. [Toolchain provenance](../evidence/wsl2-toolchain.json) records the archive URL and hash. No system package installation is required.

Linux Vite integrations pass within WSL2. A Windows PowerShell mutator distinguishes UNC writes to Linux storage from Windows-origin writes to mounted NTFS. Only the latter native watcher stayed stale; polling passed. This reproduces [Vite's documented limitation](https://vite.dev/config/server-options#server-watch). See [current results](current-results.md).

## Oracle deadline and output bounds

Simulation exposed false passes after process exit or after a late matching observation. Liveness and deadline checks now precede success. A real trickling HTTP fixture then exceeded its scenario budget despite a socket timeout. HTTP reads now run in a terminable worker with a body-size cap. Slow-body and oversized-response regressions pass. OS scheduling and file-read latency remain outside real-time guarantees. See cycles 2–6.

## Browser observation-file race

The first 20-round Chrome matrix exited after six successful updates because Windows temporarily denied renaming the observation file while the Python oracle read it. The browser adapter now retries only transient Windows permission/busy rename errors, up to about 500 ms of deliberate waits. A new matrix passed all 120 positive DOM updates with one retained session per scenario, plus the expected-stale control. The original failure remains saved; see cycles 20–22.

## Evidence preservation and log bounds

An existing matrix directory was previously accepted, allowing evidence to be overwritten. Matrix scripts now require a fresh directory. A controlled regression confirms the old summary bytes remain intact.

Retained log length was limited, but an unbounded `readline()` could first allocate a large line. Capture now drains chunks of at most 2,048 characters and retains at most 2,000 characters per line. External mutators and version commands use the same bounded readers. Simulated and real noisy-command/timeout tests pass; see cycles 23–28. Evidence path redaction also handles mixed or multiply escaped Windows separators, and saved outcomes are retained unchanged.

## Local Git ownership during approved writes

The sandbox-created repository belongs to the sandbox account, while approved Git writes run as the Windows host account. Git therefore rejected staging with a dubious-ownership diagnostic. Use a per-command `safe.directory` value scoped to this verified project checkout for approved writes. No global Git setting is required. Test execution and source-file writes were unaffected.

## Debian VM bootstrap and evidence recording

The guest installed from a Debian 12.14 image reports Debian 12.15 at execution time. It is a VMware VM with two vCPUs and approximately 2 GiB memory, separate from the Kali WSL2 runs. Its Python 3.11.2 tarfile API lacks the newer extraction filter. The portable Linux bootstrap validates paths and link destinations, verifies the official Node archive checksum, and supports this older API for that verified archive. Runtime storage is project-local under ignored reports.

Missing Git originally prevented the test recorder from saving results after execution. Git metadata is now optional; unknown working-tree state is null, and archive runs can supply a source revision. Recorder and runner SHA-256 values preserve identification of the executed files. Targeted tests, the Windows regression, and the actual VM suite pass; see cycles 32–37 and 44 in [the test log](test-log.md).

When synchronizing artifacts back to the guest, compare and retain byte-identical existing evidence instead of rewriting it. The final readiness sync initially stopped with PermissionError on a pre-existing provisioning record; retaining identical records completed the transfer and all 289 archive files then matched their committed content. Backup existing documentation before replacing it, and reject evidence whose bytes differ. No ownership changes or root privileges were needed for recovery.

## Debian browser provisioning recovery and rollback

Browser dependency installation first failed because an active installation-CD source blocked APT update. The original sources file was backed up in `reports/apt-sources.list.before` before commenting the single inspected CD-ROM entry. A subsequent download failure was resolved with a per-command APT configuration using IPv4, retries, and timeouts. This observed recovery does not establish IPv6 as the sole cause. The fresh pre-browser package baseline preserves unrelated Git installation work.

The successful browser dependency step added 84 packages, upgraded none, and added 32 manual package marks. [Package changes](../evidence/debian-vm-package-changes.json) and [source changes](../evidence/debian-vm-apt-source-change.json) identify backups and rollback references. Before rollback, inspect the current package state and any later user additions; do not blindly remove packages or restore an old package database. No desktop environment was installed.

Direct guest Chromium downloads failed with read timeouts and a DNS error. Exact pinned archives were downloaded over HTTPS on the host, transferred to the VM, and checked for matching SHA-256 values. The normal Playwright installer used a temporary localhost mirror, which was then shut down. [Download provenance](../evidence/debian-vm-browser-download-provenance.json) records URLs, sizes, and transfer hashes; these are not claimed as publisher signatures. Failures and successful retries are retained separately in cycles 38–43. Actual DOM/HMR testing and post-test process checks are recorded independently of provisioning.

## Additional browser engines and selector validation

The adapter now selects Chromium, Firefox, or WebKit explicitly; Chromium retains its existing Chrome/channel default. Channels are omitted for Firefox/WebKit. A real Node boundary test exposed inherited object keys such as `toString` reaching the launch path through ordinary object lookup. An explicit Map of the allowed engines resolves that issue before Vite is spawned. The failure and repaired verification remain in cycles 55–56; actual Chrome integration passes after repair. Engine/channel and exact browser versions are recorded in matrices. Playwright WebKit on Debian is not Safari verification.

The post-browser process inspector now checks every live executable under project-local runtime/browser storage, extending the earlier Node/Chromium name list to cover Firefox and WebKit descendants. It reports rather than kills unrelated live processes; run it after browser experiments have finished.

## Additional Debian dependencies and interrupted downloads

Firefox/WebKit binary archives were acquired from the pinned manifest over host HTTPS, verified after transfer, and installed using the normal installer through a temporary local mirror. Missing shared libraries were reported separately from installer exit 0. APT first failed over HTTP; a scoped official-source HTTPS override then fetched most archives but left two failures. Actual archive probes observed intermittent DNS failures and successful HTTP/HTTPS requests, so no sole protocol cause is asserted.

The exact two remaining `.deb` files were downloaded on the host and checked against SHA-256 and sizes from guest APT metadata before populating the package cache. The normal installer then added 228 packages and changed no existing package versions. [Final package changes](../evidence/remaining-browser-dependencies-cache.json), [archive metadata](../evidence/remaining-browser-apt-cache-provenance.json), and the failed attempts in the test log are retained. Fresh package/manual-mark baselines and prior adapter files are under `reports/remaining-engines-before/`; review subsequent user additions before any rollback. The HTTPS override applies only to the command, and system source content remains unchanged.

The initial ad hoc network probe matched `.deb` inside repository hostnames. Requiring a complete archive URL corrected that diagnostic; its original DNS results are retained and explicitly excluded from reachability conclusions. Provisioning console logs retain their original whitespace under the scoped evidence attribute.

## HTTP polling slices and startup starvation

The readiness suite exposed HTTP baseline failures even though Vite had become ready within its scenario budget. A controlled real worker delayed by 650 ms confirmed that repeatedly killing it at each 500 ms polling slice prevented completion. The worker now retains one request across slices; the parent still enforces the whole observation deadline, cancels pending work at the observation boundary, and discards pending results when URL/body limit changes. A socket read no longer imposes an unrelated 500 ms request budget. Pending samples preserve a previous match's sampling window, but only a subsequent actual matching response can pass; deadline and process-liveness checks still precede success.

Real delayed startup/headers, oversized responses and slow trickling bodies pass their targeted checks. Current Windows and Debian full suites pass, and a fresh Windows 120-update Vite endpoint matrix verifies repeated request reuse. The stale-file fixture also needed a separate 3-second startup allowance; its 350 ms mutation observation policy remains unchanged. Failed and repaired evidence is retained in cycles 69–73 and 81–84. Scheduler latency and sampled observation limits still apply.

## CLI report export and package metadata

An existing directory passed as `--report` originally raised an uncaught write exception. Report creation/write OSError now produces a controlled CLI error and exit 2; successful report export is checked by the installed console integration. See cycles 74–75 and 80.

The old `setuptools>=61` floor allowed 76.1.0, which rejected the SPDX string `license = "MIT"` in an actual build. The requirement is now `>=77.0.3`, following the [official packaging guidance](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) and [setuptools SPDX support documentation](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html). Exact backend wheels were verified against [PyPI metadata](../evidence/build-backend-provenance.json). A build with precisely 77.0.3, wheel license/module inspection, fresh venv install and file/slow-HTTP/invalid-input console tests passed on Windows, outside the source checkout.

The new package smoke harness initially decoded UTF-8 output using Windows CP1252 and named an HTTP fixture `http.py`, shadowing the standard library. Explicit UTF-8 capture and a distinct fixture name repaired those harness failures without changing runner behavior for a correctly detected failed process. All intermediate results remain in cycles 76–80. Those limits were historical: later cycles verify Debian installed wheel/sdist and actual CI Python 3.10 source execution; current release gates are in [readiness](readiness.md).

## Installed starter creation and interpreter identity

Running a venv's `python -m` from the checkout can import checkout code first. The Debian older checkout exposed this in the application-state gate: tokens updated, but the source-created starter lacked the new retained-state selector. Create installed starters from an independent directory and assert the imported module lies within `sys.prefix`. Keep failed/source-created matrices and repeat acceptance with clean creation. Separately, resolving the Linux venv Python symlink selected the system interpreter and lost its installed package; use its absolute launcher path without resolving the symlink. Cycles 100–111 retain both setup faults and genuine installed repeats.

## Windows account consistency and UTF-8 controllers

Starter files staged under the sandbox account inherited creator permissions that an approved host pnpm process could not read. Creating the venv/starter and installing/testing under one Windows account resolved the confirmed EPERM setup issue; no global ACL changes were made. Existing failed directories remain under ignored reports. This is a setup-account boundary, not evidence of a watch freshness defect.

Git capture also decoded UTF-8 Unicode paths with CP1252. Use explicit UTF-8, a five-second capture budget and per-command project-scoped Git trust. A real temporary Unicode Git repository verifies the recorder without requiring `.git` on archive guests. Later special-filename package checks needed explicit UTF-8 JSON reads too. Cycles 96–98 and 135–136 preserve failures and repairs.

## Recoverable reports and generic application observations

Partial direct report writes could truncate an existing report. Stage in the destination directory, flush/fsync and replace only completed content, removing the temporary file after failure. Controlled active write/rename faults verify that prior report bytes remain intact. This does not promise durability after every possible storage/power failure; see cycles 90–91.

The adapter now creates its own per-document identity, accepts DOM/click/state selectors, and checks a multi-module counter application without requiring fixture-owned globals. Metrics distinguish sampled DOM changes from application-supplied HMR callbacks. Actual installed native/polling matrices with all three mutation modes and stale controls verify the selected Windows/Debian engines; other framework/state contracts require their own scenarios.

## Captured-command cancellation on Windows

A controlled installed SIGINT during a 30-second external mutator exceeded the controller deadline because a long process-handle wait did not promptly return to Python signal handling. Poll completion in at most 100 ms slices while preserving the total deadline and bounded capture/cleanup. Installed Windows/Debian cancellation covers startup, pending HTTP, mutator descendants and live browser trees. Failure cleanup in test controllers uses only PIDs published or observed under their own launched process. Cycles 125–133 retain the failure, repair and actual process checks; this is controlled signal delivery, not physical keypress or detached-process containment.

## Reproduction and CI naming contracts

The original reproduction text interpolated an unquoted filename and assumed a `python` alias. Reports now add literal `argv`, use the current interpreter, and label quoted PowerShell/POSIX presentation. Real shell execution of spaces/apostrophe/dollar-sign/Unicode filenames and installed argv repetition verify behavior; original cwd/environment/dependencies remain necessary. Schema 1 consumers must tolerate additive fields. Cycles 132–137 retain the checks and the separate controller decoding failure.

The first actual CI run normalized Python-version dots in recorder filenames, but analyzer/upload patterns expected dots. Share `normalize_label` for lookup and derive the artifact suffix using the same function. Always assess a saved failed test cycle before stopping later gates; required assessment rejects failures/skips/empty runs/wrong revisions. First-run logs also show Windows 3.12/3.14 source errors; their case-level evidence was not uploaded, so causes remain unassigned until the repaired retention run supplies it. Cycles 138–139 record this limitation rather than attributing a speculative product fault.

## Owned Windows temporary workspace sharing violations

The second CI run retained WinError 32/5 during temporary directory deletion. A cwd-only child did not reproduce locally; an actual directory handle opened without delete sharing did. Retry deletion of the already-owned TemporaryDirectory for at most two seconds and only those Windows permission boundaries, propagating persistent/unrelated errors. This verifies the filesystem boundary, not the identity of the CI handle holder. Cycles 144–147 preserve both the non-reproduction and controlled failure/repair.

The next CI exposed Python 3.10.11's recursive TemporaryDirectory permission handler under the same controlled handle. Use explicit Windows rmtree with a nonrecursive handler, resetting only owned read-only entries and preserving bounded retries. Disarm the stdlib finalizer before attempts so a persistent failure retains the diagnostic root without an unbounded second recovery. Linux keeps standard cleanup. Actual Windows handle, read-only file and genuine persistent-finalizer checks passed locally (cycles 156–158); compatibility with all supported Python versions remains a required remote gate.

## Generated Vite starter write stability

The second CI Windows browser overwrite matrix observed empty DOM after eleven valid updates. A controlled 120ms truncate/write interval independently exposed empty DOM on native and polling watchers. Generated starters now explicitly wait for 200ms stable file size, checked every 20ms via Chokidar awaitWriteFinish. Native/polling labels describe the underlying watcher with this added policy; historical research fixtures remain unfiltered. The exact nonempty-token oracle is unchanged, reload/counter loss still invalidate continuity and disabled watch must remain stale. Cycles 148–149 verify short-write recovery without claiming that all interruption lengths are safe or that the CI event has one proven cause. Adapted/bundled-dev backends require their own verified options. Matrix controllers now retain all seven cases, including the stale control, before failing the combined assessment.

## Source identity during recorded tests

Cycle 146 loaded original code before a repair was applied, while its end-only hash described newer disk bytes. Preserve that cycle as mixed identity. Snapshot source inputs before test discovery/import and after execution; expose both maps and an explicit change flag, and reject changed/unreadable inputs in required CI. Tests mutate only a temporary source fixture. These endpoints cannot detect edit-and-restore, so freeze source throughout every cycle. Cycle 150 verifies the contract; historical records retain their original weaker metadata.

## Cancellation controller process creation identity

The d7100e3 Windows Python 3.14 CI cancellation returned 130 within the bound but its PID-only ancestry closure listed about 160 processes and failed liveness. A controlled recycled-parent graph confirmed that closure can adopt older unrelated processes; missing historical birth metadata prevents assigning that run a sole cause. [Microsoft documents reused parent PIDs and creation-date comparison](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process). Acceptance controllers now require parent/child creation ordering and exact PID plus birth identity for liveness. Windows emergency cleanup verifies and terminates through the same process handle; Linux uses pidfd. Query errors fail the check. Actual owned-child and installed Windows cancellation passed in cycles 175–176; hosted compatibility and VM verification remain required. Product package bytes are unchanged. The pre-repair graph fixture retains the original function separately so it remains reproducible after the repair.

The next CI Windows3.12 helper timed out in external PowerShell/CIM enumeration. The current observer uses [Toolhelp process snapshots](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot) and exact GetProcessTimes birth ticks directly. Generations born after capture begins are excluded to prevent a reused PID from inheriting an old snapshot row. Protected global processes that cannot be queried are outside its observation scope; errors on previously observed owned records still fail. Actual child/handle checks passed on Python3.12 and3.10, and real Chrome cancellation passed in cycles189–191. This auxiliary change does not modify package payload.

## Python 3.10 captured-command signal delivery

The same CI separately timed out during installed generic mutation cancellation on Windows3.10.11. A project-local official embedded runtime, manually unpacked old wheel, unchanged deadlines and retained phase/stack diagnostics reproduced it. The interrupt thread returned from raise_signal, but the main thread stayed in repeated short subprocess-handle waits. A controlled child comparison caught SIGINT after4.11s with handle waits versus0.203s with interruptible sleep. Replace captured-command waits with poll plus at most50ms interruptible sleep, preserving the total deadline and existing cleanup. Actual repaired-candidate Python3.10 startup/HTTP/mutation cancellation and noisy/failed/deadline mutation checks passed in cycle188. This product change supersedes the old wheel and requires new hosted pip/venv and same-byte Windows/Debian acceptance; embedded diagnostics do not count as that release gate. Phase timelines and partial output/thread stacks are now retained on both success and timeout.

## File starter read sharing during atomic replacement

- Symptom: the installed file starter exited on Windows atomic update7 with PermissionError from input read; the runner correctly rejected the result (Cycle195).
- Reproduction: a real exclusive Windows file handle denied reads temporarily; the original worker crashed (Cycle196). No injected read exception was used.
- Fix: the sample worker retries missing input or Windows EACCES reads for one second per continuous outage, resetting after a successful read. Persistent faults and unrelated output errors propagate. The fixture cancels and joins its handle-release thread before directory cleanup.
- Verification: focused real Windows Python3.12 and Python3.10 checks passed (Cycles197/198); 61-test Windows source gate passed (199), and fixture cleanup passed (200). Linux and freshly rebuilt package acceptance remain required. The runner oracle and total observation deadline were unchanged; this example does not promise recovery from longer outages or arbitrary filesystem errors.
