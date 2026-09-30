# Current verification results — 2026-09-30

This is an experimental pilot with recorded repairs and real-tool evidence. It has not established a new Vite defect, a gap in Vite's existing tests, or the research go/no-go criterion. [Every cycle, including failures](test-log.md), records its analysis and follow-up.

## Completed 20-round matrices

Each watcher column contains three mutation modes × 20 rounds. Each scenario uses a fresh isolated fixture. These observations are freshness checks, not comparable performance benchmarks.

| Execution and mutation origin | Native watcher | Polling watcher | Evidence |
| --- | --- | --- | --- |
| Windows Vite, Windows-local writes on NTFS | 60/60 passed | 60/60 passed | [Endpoint matrix](../evidence/matrices/windows-repaired-2026-09-30/summary.json) |
| Linux Vite in WSL2, Linux-local writes | 60/60 passed | 60/60 passed | [Endpoint matrix](../evidence/matrices/wsl2-linux-side-2026-09-30/summary.json) |
| Linux Vite in WSL2, Windows PowerShell writes through UNC to Linux storage | 60/60 passed | 60/60 passed | [UNC matrix](../evidence/matrices/windows-to-wsl2-unc-20260930T120225Z/summary.json) |
| Linux Vite in WSL2, Windows PowerShell writes to mounted Windows NTFS | 60/60 stale | 60/60 passed | [Mounted-NTFS matrix](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T125228Z/summary.json) |
| Windows Vite, actual Chrome DOM and HMR continuity | 60/60 passed | 60/60 passed | [Browser matrix](../evidence/matrices/windows-chrome-hmr-repaired-2026-09-30/summary.json) |

Windows, Linux-side WSL2, and browser matrices each include a disabled-watcher control that correctly returned stale. The browser positive scenarios retain the page session and observe at least 20 HMR callbacks per scenario. The first browser matrix failed on an observation-file publication race; its evidence is retained and the repair is documented.

The mounted-NTFS native result reproduces the [documented Windows-origin WSL2 watcher limitation](https://vite.dev/config/server-options#server-watch). The UNC/Linux-storage result is a separate observation; neither implies behavior on every WSL installation.

## Regression checks

- [Windows complete suite](../evidence/test-runs/20260930T130654Z-final-windows-7d98e7.json): 21 tests passed, zero skips.
- [WSL2 complete suite](../evidence/test-runs/20260930T130852Z-final-linux-wsl2-f136bd.json): 19 tests passed, two Windows-browser tests explicitly skipped.
- After bounded command capture changed, targeted cross-origin repeats retained the same results: [UNC](../evidence/matrices/windows-to-wsl2-unc-20260930T131405Z/summary.json), [mounted NTFS](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T131542Z/summary.json), two rounds per combination on each path.
- [Artifact audit](../evidence/test-runs/20260930T131816Z-artifact-audit-fb3a0c.json): three checks passed for saved JSON, matrix summary agreement, document links, and user-home path redaction.
- Controlled simulations test deadline decisions, process-exit decisions, invalid CLI input, log-read bounds, and evidence preservation.
- Real integrations test generated files, HTTP output, slow and oversized HTTP bodies, launcher descendants, noisy or failed/timed-out mutation commands, Vite, Windows-origin writes, and Windows Chrome DOM updates.

## Recorded environment

Vite 8.3.1 and Playwright Core 1.62.1 are pinned in the lockfile. Windows runs used Node 24.18.0, Python 3.12.14, Windows 11 build 26200, and NTFS. WSL2 used Kali Linux, Python 3.13.12, Linux Node 24.18.0, and kernel `6.18.33.2-microsoft-standard-WSL2`. The Linux workspace's `stat` filesystem label was `ext2/ext3`; this label is recorded without inferring a more specific filesystem. The browser matrix used Chrome 154.0.8037.58. [Linux toolchain provenance](../evidence/wsl2-toolchain.json) records the official archive checksum.

## Remaining limits

Bare-metal Linux and Linux browser execution are unavailable in this environment. Other browser engines and application-specific HMR behavior have not been tested. Timing budgets and extraction rules are scenario policies; stable samples cannot prove indefinitely correct output. Process containment covers ordinary descendants, with deliberately detached or cross-OS escape outside the contract. Novelty and maintainer usefulness still need external validation.
