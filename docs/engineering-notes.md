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
