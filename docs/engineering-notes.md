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

## Debian browser provisioning recovery and rollback

Browser dependency installation first failed because an active installation-CD source blocked APT update. The original sources file was backed up in `reports/apt-sources.list.before` before commenting the single inspected CD-ROM entry. A subsequent download failure was resolved with a per-command APT configuration using IPv4, retries, and timeouts. This observed recovery does not establish IPv6 as the sole cause. The fresh pre-browser package baseline preserves unrelated Git installation work.

The successful browser dependency step added 84 packages, upgraded none, and added 32 manual package marks. [Package changes](../evidence/debian-vm-package-changes.json) and [source changes](../evidence/debian-vm-apt-source-change.json) identify backups and rollback references. Before rollback, inspect the current package state and any later user additions; do not blindly remove packages or restore an old package database. No desktop environment was installed.

Direct guest Chromium downloads failed with read timeouts and a DNS error. Exact pinned archives were downloaded over HTTPS on the host, transferred to the VM, and checked for matching SHA-256 values. The normal Playwright installer used a temporary localhost mirror, which was then shut down. [Download provenance](../evidence/debian-vm-browser-download-provenance.json) records URLs, sizes, and transfer hashes; these are not claimed as publisher signatures. Failures and successful retries are retained separately in cycles 38–43. Actual DOM/HMR testing and post-test process checks are recorded independently of provisioning.
