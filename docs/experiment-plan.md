# Experiment plan

## Question

Can a black-box runner detect when a supported watch workflow serves old output after a file mutation, while avoiding false alarms from normal rebuild latency? The initial adapter requests a Vite-transformed JavaScript module over HTTP and extracts a unique token from the response. A passing response proves only that this endpoint returned the current token during the observation window. It does not prove that browser HMR applied the update.

Vite already tests HMR in its playground and uses polling during those tests. Watchwoman already has a black-box Watchman parity suite. We have not established that this project finds an uncovered failure in either suite.

## Architecture

1. **Scenario:** JSON specifies a fixture, argv command, mutation target, optional source template, output oracle, and time policy.
2. **Runner:** copies the fixture into a temporary workspace, starts the command without a shell, captures logs, and stops its process tree.
3. **Mutator:** writes a unique token by overwrite, atomic replacement, or burst. For source templates, the intermediate burst write is valid source too.
4. **Oracle:** reads a file or HTTP response, optionally extracts exactly one capture group, and compares its bytes with the expected token. It requires a stable match for the configured interval.
5. **Reporter:** records per-round status and hashes, latency distribution, environment, filesystem type when discoverable, tool version, and reproduction inputs in JSON.

## Matrix and evidence

| Environment | Native watcher | Polling control | Mutations | Repetitions |
| --- | --- | --- | --- | --- |
| Windows local filesystem | Vite scenario | Vite scenario | overwrite, atomic replace, burst | At least 20 each |
| Physical Linux local filesystem (unverified) | Vite scenario | Vite scenario | overwrite, atomic replace, burst | At least 20 each |
| Debian VMware guest-local Linux filesystem | Vite scenario | Vite scenario | same three | At least 20 each |
| WSL2 Linux filesystem, edit from WSL2 | Vite scenario | Vite scenario | same three | At least 20 each |
| WSL2 Linux filesystem, Windows writes through UNC | Vite scenario plus Windows mutator | Vite polling control | same three | At least 20 each |
| WSL2 mounted Windows NTFS, Windows writes | Vite scenario plus Windows mutator | Vite polling control | same three | At least 20 each |
| Windows Chrome DOM and HMR session | Browser adapter with native watching | Browser adapter with polling | same three | At least 20 each |
| Debian VMware Linux Chromium DOM and HMR session | Browser adapter with native watching | Browser adapter with polling | same three | At least 20 each |

For every run, retain raw JSON and the exact Vite, Node, Python, OS, and filesystem details. Run each case from a clean fixture copy. A new port and process are allocated per run. Do not compare latency between environments as a benchmark without controlling machine load and storage.

## Decision rule

Investigate any `stale` or `timeout` result using the saved hashes and logs. Repeat the same configuration at least three times, compare native and polling behavior, and check whether the workflow is supported by the tool. Compare a minimal reproduction with existing Vite tests before calling it a coverage gap. Continue as a standalone project only if a supported-workflow failure is repeatable and missed by existing tests, or two maintainers say this reusable harness fills a need. Otherwise offer the fixture to an existing test suite. No failure in this matrix would not prove absence of bugs.

## Current evidence and limits

The [current results](current-results.md) complete the Windows, WSL2 Linux-side, Windows-origin UNC, Windows-origin mounted-NTFS, Windows Chrome, Debian VM endpoint, and Debian Chromium rows with 20 rounds per watcher/mutation combination. Disabled-watcher controls detect deliberately stale output. The mounted-NTFS native stale result agrees with the documented Vite WSL2 limitation; it does not establish a new uncovered defect.

The generic file oracle also has generated-output integration tests. The browser adapter observes real DOM tokens and HMR callbacks with page-session continuity, covering one dependency-accept fixture. HTTP results remain endpoint checks. Python's controlled time/process simulations establish decision behavior, while real slow HTTP, subprocess cleanup, Vite, Windows PowerShell, and Chrome runs establish the tested integrations.

Physical Linux hardware, Linux distributions beyond the observed Debian/Kali environments, and other browser engines remain unverified. VM and WSL2 evidence cannot substitute for physical hardware. Timing and extract regex are scenario-defined and may need tuning per tool. Browser HMR coverage in Vite already exists, and maintainer confirmation or a supported-workflow coverage gap has not yet been established.

Sources: [Vite contributing guide](https://github.com/vitejs/vite/blob/main/CONTRIBUTING.md), [Vite server watch options](https://vite.dev/config/server-options#server-watch), [Watchwoman project](https://github.com/radiosilence/watchwoman).
