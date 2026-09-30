# Current verification results — 2026-10-01

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
| Debian VMware Vite, guest-local Linux writes | 60/60 passed | 60/60 passed | [VM endpoint matrix](../evidence/matrices/debian-vm-endpoint-2026-09-30/summary.json) |
| Debian VMware Vite, actual Linux Chromium DOM and HMR continuity | 60/60 passed | 60/60 passed | [VM browser matrix](../evidence/matrices/debian-vm-chromium-hmr-2026-09-30/summary.json) |
| Windows Vite, installed Microsoft Edge DOM and HMR continuity | 60/60 passed | 60/60 passed | [Edge matrix](../evidence/matrices/windows-edge-hmr-remaining-2026-09-30/summary.json) |
| Debian VMware Vite, Playwright Firefox DOM and HMR continuity | 60/60 passed | 60/60 passed | [Firefox matrix](../evidence/matrices/debian-firefox-hmr-2026-10-01/summary.json) |
| Debian VMware Vite, Playwright WebKit DOM and HMR continuity | 60/60 passed | 60/60 passed | [WebKit matrix](../evidence/matrices/debian-webkit-hmr-2026-10-01/summary.json) |

Windows, Linux-side WSL2, Debian VM, and browser matrices each include a disabled-watcher control that correctly returned stale. The browser positive scenarios retain the page session and observe at least 20 HMR callbacks per scenario. The first Windows browser matrix failed on an observation-file publication race; its evidence is retained and the repair is documented.

The mounted-NTFS native result reproduces the [documented Windows-origin WSL2 watcher limitation](https://vite.dev/config/server-options#server-watch). The UNC/Linux-storage result is a separate observation; neither implies behavior on every WSL installation.

## Regression checks

- [Latest Windows complete-suite repeat](../evidence/test-runs/20260930T150202Z-requested-windows-repeat-b0c0ae.json): 24 tests passed, zero skips, before the new engine-selection boundary test was added.
- [Debian VM complete suite](../evidence/test-runs/20260930T143705Z-debian-vm-browser-full-bd4997.json): 24 tests passed, zero skips, including real Linux Chromium.
- After engine selection changed, [Chrome](../evidence/test-runs/20260930T175643Z-browser-selector-chrome-repaired-5be44c.json), [Debian Firefox](../evidence/test-runs/20260930T180027Z-debian-firefox-integration-b544f6.json), and [Debian WebKit](../evidence/test-runs/20260930T180231Z-debian-webkit-integration-cf85dd.json) each passed all three targeted integration tests without skips, including real DOM/HMR, stale control, and invalid selection. [Edge's initial integration](../evidence/test-runs/20260930T150402Z-windows-edge-integration-db3ad6.json) passed both real-browser tests before the boundary test was added.
- After installing Firefox/WebKit libraries, [existing Linux Chromium integration](../evidence/test-runs/20260930T180801Z-debian-chromium-after-engines-a7fc41.json) passed all three tests without skips. [Expanded process cleanup](../evidence/test-runs/20260930T181025Z-debian-all-engine-cleanup-2f3562.json) found no live executable under project-local runtime/browser storage after all guest engine experiments.
- [Earlier WSL2 complete suite](../evidence/test-runs/20260930T130852Z-final-linux-wsl2-f136bd.json): 19 tests passed, two browser tests explicitly skipped. This historical run predates the three Debian support tests; WSL2 browser provisioning was not performed.
- Actual guest process inspection passed [after the suite](../evidence/test-runs/20260930T144622Z-debian-vm-browser-cleanup-f001d9.json) and [after both matrices](../evidence/test-runs/20260930T144950Z-debian-vm-matrix-cleanup-15ddc7.json): no live project-local Node/Chromium/crash-handler executable remained.
- After bounded command capture changed, targeted cross-origin repeats retained the same results: [UNC](../evidence/matrices/windows-to-wsl2-unc-20260930T131405Z/summary.json), [mounted NTFS](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T131542Z/summary.json), two rounds per combination on each path.
- [Latest artifact audit including added browser engines](../evidence/test-runs/20260930T181438Z-remaining-browser-artifact-audit-9127c7.json): three checks passed for saved JSON, matrix summary agreement, document links, and user-home path redaction.
- Controlled simulations test deadline decisions, process-exit decisions, invalid CLI input, log-read bounds, and evidence preservation.
- Real integrations test generated files, HTTP output, slow and oversized HTTP bodies, launcher descendants, noisy or failed/timed-out mutation commands, Vite, Windows-origin writes, Windows Chrome/Edge, and Debian Chromium/Firefox/WebKit DOM updates.

## Recorded environment

Vite 8.3.1 and Playwright Core 1.62.1 are pinned in the lockfile. Windows runs used Node 24.18.0, Python 3.12.14, Windows 11 build 26200, and NTFS. WSL2 used Kali Linux, Python 3.13.12, Linux Node 24.18.0, and kernel `6.18.33.2-microsoft-standard-WSL2`. The Linux workspace's `stat` filesystem label was `ext2/ext3`; this label is recorded without inferring a more specific filesystem. The browser matrix used Chrome 154.0.8037.58. [Linux toolchain provenance](../evidence/wsl2-toolchain.json) records the official archive checksum.

The [Debian guest](../evidence/debian-vm-environment.json) reports 12.15, although installed from a 12.14 image, with VMware virtualization, two vCPUs, 1,978,232 KiB memory, Python 3.11.2, and kernel `6.1.0-53-amd64`. Its filesystem label is also `ext2/ext3`. It used Node 24.18.0 and Chrome for Testing 151.0.7922.34 (Chromium revision 1234). [Toolchain provenance](../evidence/debian-vm-toolchain.json) and [browser download provenance](../evidence/debian-vm-browser-download-provenance.json) record acquisition details. Tests ran from archive revision da9270c plus the recorded support updates; recorder and runner hashes identify executed code.

Provisioning failures on the installation-CD APT source and network/browser downloads are retained separately from successful software tests. Relevant backups and package changes are described in [engineering notes](engineering-notes.md). SSH-only operation was sufficient; no desktop environment was installed.

Additional coverage uses installed Edge 154.0.4258.37 on Windows and pinned Playwright Firefox 153.0 revision 1538 / WebKit 26.5 revision 2336 in the same Debian guest. [Archive provenance](../evidence/remaining-browser-download-provenance.json) records transfer hashes, and [adapter provenance](../evidence/remaining-browser-adapter-provenance.json) identifies the c73827a base plus source overlays. Additional libraries added 228 packages without changing existing package versions. The command-scoped HTTPS source override preserves system source content, [verified by SHA-256](../evidence/remaining-browser-source-verification.json); [final package changes](../evidence/remaining-browser-dependencies-cache.json) and failed attempts remain recorded. Playwright WebKit on Debian is not Safari verification.

## Remaining limits

Physical Linux hardware remains unverified. Safari on macOS/iOS, additional browser/platform combinations, and application-specific HMR behavior have not been tested. The browser results cover one dependency-accept fixture. Timing budgets and extraction rules are scenario policies; stable samples cannot prove indefinitely correct output. Process containment covers ordinary descendants, with deliberately detached or cross-OS escape outside the contract. Novelty and maintainer usefulness still need external validation.
