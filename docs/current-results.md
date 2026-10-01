# Current verification results — 2026-10-01

The installed 1.0.0 candidate supplies file/HTTP/DOM starters, side-effect-free preflight, dependency diagnostics, recoverable JSON export, summaries, quoted reproduction and controlled cancellation. Local installed application workflows are verified; required remote release CI is in progress. No new Vite defect, upstream coverage gap or research go/no-go criterion is inferred. [Every cycle, including failures](test-log.md), records its analysis and follow-up.

The [readiness assessment](readiness.md) separates current release gates from historical experiments. The 30-test readiness suites and older research matrices below predate the installed-product work.

## Installed application acceptance

Each positive matrix is native/polling × overwrite/atomic replacement/burst × 20 updates (120 total), with one expected-stale disabled control and original fixture-byte preservation. Browser matrices also require an independent document identity and the clicked counter's retained state. These application metrics count sampled DOM changes; historical fixture metrics below count application callbacks.

| Workflow | Installed creation and execution | Evidence |
| --- | --- | --- |
| Windows HTTP, revised lifecycle candidate | 120/120 positive; stale control passed | [Matrix](../evidence/matrices/release-r2-windows-http-1.0.0/summary.json) |
| Windows Chrome, independent multi-module starter | 120/120 positive; state/session/control passed | [Matrix](../evidence/matrices/installed-windows-chrome-clean-init-1.0.0/summary.json) |
| Windows Edge, same application | 120/120 positive; state/session/control passed | [Matrix](../evidence/matrices/installed-windows-edge-clean-init-1.0.0/summary.json) |
| Debian Chromium, same application | 120/120 positive; state/session/control passed | [Matrix](../evidence/matrices/installed-debian-chromium-clean-init-1.0.0/summary.json) |
| Debian Firefox, same application | 120/120 positive; state/session/control passed | [Matrix](../evidence/matrices/installed-debian-firefox-clean-init-1.0.0/summary.json) |
| Debian Playwright WebKit, same application | 120/120 positive; state/session/control passed | [Matrix](../evidence/matrices/installed-debian-webkit-clean-init-1.0.0/summary.json) |
| Debian HTTP, independent installed starter | 120/120 positive; stale control passed | [Matrix](../evidence/matrices/installed-debian-http-clean-init-1.0.0/summary.json) |

Artifacts evolved during acceptance: [initial candidate](../evidence/release-candidate-1.0.0-manifest.json), [diagnostics repair](../evidence/release-final-1.0.0-manifest.json), and [lifecycle repair](../evidence/release-1.0.0-r2-manifest.json). Browser/fixture assets stayed identical across those builds; later report reproduction fields are additive. Earlier matrices identify their tested artifact and are not claimed as byte-identical final-release acceptance. Final CI builds and tests its own artifacts; release identity will link the selected accepted artifact.

Current source regression before the final report fields passed 46/46 without skips on [Windows](../evidence/test-runs/20260930T215533Z-release-r2-source-windows-84113d.json) and [Debian](../evidence/test-runs/20260930T215740Z-release-r2-source-debian-6cfaf8.json). Actual [Windows](../evidence/test-runs/20260930T220119Z-reproduction-filename-after-ac56b2.json) and [POSIX](../evidence/test-runs/20260930T220715Z-reproduction-posix-debian-239ba2.json) shell checks verify the later special-filename reproduction. [Installed sdist/wheel rebuild](../evidence/test-runs/20260930T220700Z-release-reproduction-package-utf8-ecc3f9.json) verifies current installed argv, versions and all starters.

Controlled installed interruption covers startup, pending HTTP, external mutator/ordinary descendants and a live browser on [Windows mutation](../evidence/test-runs/20260930T215300Z-installed-cancel-mutation-repaired-85bba3.json), [Windows browser](../evidence/test-runs/20260930T215430Z-installed-browser-cancel-windows-993007.json) and [Debian](../evidence/test-runs/20260930T215955Z-release-r2-debian-cancel-a61a5a.json). [Current Debian process inspection](../evidence/test-runs/20261001T064719Z-release-debian-final-process-inspection-ff66fe.json) found no project-local runtime/browser survivor. Signals were self-delivered in a real CLI process, not physical keyboard events.

The [current WSL2 source repeat](../evidence/test-runs/20260930T214613Z-final-linux-wsl2-2f9957.json) collected 46, passed 43 and explicitly skipped three unprovisioned browser tests. It does not count as WSL2 browser verification. The [first actual CI](../evidence/ci/first-run-36783229577/jobs.json) passed all 47 source checks on Ubuntu Python 3.10/3.12/3.14 and Windows 3.10, but analysis/artifact label mismatches stopped all jobs; Windows 3.12/3.14 additionally reported source errors. Corrected retention CI is running and must identify those failing cases before release.

## Historical research 20-round matrices

Each watcher column contains three mutation modes × 20 rounds. Each scenario uses a fresh isolated fixture. These observations are freshness checks, not comparable performance benchmarks.

| Execution and mutation origin | Native watcher | Polling watcher | Evidence |
| --- | --- | --- | --- |
| Windows Vite, Windows-local writes on NTFS, after readiness HTTP repair | 60/60 passed | 60/60 passed | [Latest endpoint matrix](../evidence/matrices/windows-readiness-http-2026-10-01/summary.json) |
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

- [Current Windows complete suite](../evidence/test-runs/20260930T192901Z-readiness-windows-repaired-78db90.json): 30 tests passed, zero skips, after HTTP polling, CLI report and fixture startup repairs, including real Chrome/Vite and stale controls.
- [Current Debian VM complete suite](../evidence/test-runs/20260930T193050Z-readiness-debian-full-c6c072.json): 30 tests passed, zero skips, including real Linux Chromium and new HTTP/CLI boundaries. [Post-suite process inspection](../evidence/test-runs/20260930T193151Z-readiness-debian-cleanup-151fc2.json) passed without live project-local runtime/browser executables.
- [Installed Windows package integration](../evidence/test-runs/20260930T191902Z-installed-package-complete-df4c90.json): exact minimum setuptools 77.0.3 wheel build, MIT metadata and module contents, isolated venv installation, import/console outside checkout, file updates/report export, slow HTTP responses and invalid-input handling passed. [The earlier permitted backend failure](../evidence/test-runs/20260930T190915Z-permitted-backend-build-before-7faa94.json) remains recorded.
- [Initial readiness review](../evidence/test-runs/20260930T184029Z-readiness-windows-full-3094c2.json) failed three baseline checks. Controlled regressions identified HTTP worker starvation and a too-short stale-fixture startup policy. Independent CLI export and build-floor faults were also found and repaired. Every intermediate result remains in cycles 69–84 of [the test log](test-log.md).
- After engine selection changed, [Chrome](../evidence/test-runs/20260930T175643Z-browser-selector-chrome-repaired-5be44c.json), [Debian Firefox](../evidence/test-runs/20260930T180027Z-debian-firefox-integration-b544f6.json), and [Debian WebKit](../evidence/test-runs/20260930T180231Z-debian-webkit-integration-cf85dd.json) each passed all three targeted integration tests without skips, including real DOM/HMR, stale control, and invalid selection. [Edge's initial integration](../evidence/test-runs/20260930T150402Z-windows-edge-integration-db3ad6.json) passed both real-browser tests before the boundary test was added.
- After installing Firefox/WebKit libraries, [existing Linux Chromium integration](../evidence/test-runs/20260930T180801Z-debian-chromium-after-engines-a7fc41.json) passed all three tests without skips. [Expanded process cleanup](../evidence/test-runs/20260930T181025Z-debian-all-engine-cleanup-2f3562.json) found no live executable under project-local runtime/browser storage after all guest engine experiments.
- [Earlier WSL2 complete suite](../evidence/test-runs/20260930T130852Z-final-linux-wsl2-f136bd.json): 19 tests passed, two browser tests explicitly skipped. This historical run predates the three Debian support tests; WSL2 browser provisioning was not performed.
- Actual guest process inspection passed [after the suite](../evidence/test-runs/20260930T144622Z-debian-vm-browser-cleanup-f001d9.json) and [after both matrices](../evidence/test-runs/20260930T144950Z-debian-vm-matrix-cleanup-15ddc7.json): no live project-local Node/Chromium/crash-handler executable remained.
- After bounded command capture changed, targeted cross-origin repeats retained the same results: [UNC](../evidence/matrices/windows-to-wsl2-unc-20260930T131405Z/summary.json), [mounted NTFS](../evidence/matrices/windows-to-wsl2-mounted-ntfs-20260930T131542Z/summary.json), two rounds per combination on each path.
- [Current readiness artifact audit](../evidence/test-runs/20260930T193842Z-readiness-artifact-audit-4d2039.json): three checks passed for saved JSON, matrix summary agreement, document links and user-home path redaction, including imported Debian results.
- Controlled simulations test deadline decisions, process-exit decisions, invalid CLI input, log-read bounds, and evidence preservation.
- Real integrations test generated files, HTTP output, slow and oversized HTTP bodies, launcher descendants, noisy or failed/timed-out mutation commands, Vite, Windows-origin writes, Windows Chrome/Edge, and Debian Chromium/Firefox/WebKit DOM updates.

## Recorded environment

Vite 8.3.1 and Playwright Core 1.62.1 are pinned in the lockfile. Windows runs used Node 24.18.0, Python 3.12.14, Windows 11 build 26200, and NTFS. WSL2 used Kali Linux, Python 3.13.12, Linux Node 24.18.0, and kernel `6.18.33.2-microsoft-standard-WSL2`. The Linux workspace's `stat` filesystem label was `ext2/ext3`; this label is recorded without inferring a more specific filesystem. The browser matrix used Chrome 154.0.8037.58. [Linux toolchain provenance](../evidence/wsl2-toolchain.json) records the official archive checksum.

The [Debian guest](../evidence/debian-vm-environment.json) reports 12.15, although installed from a 12.14 image, with VMware virtualization, two vCPUs, 1,978,232 KiB memory, Python 3.11.2, and kernel `6.1.0-53-amd64`. Its filesystem label is also `ext2/ext3`. It used Node 24.18.0 and Chrome for Testing 151.0.7922.34 (Chromium revision 1234). [Toolchain provenance](../evidence/debian-vm-toolchain.json) and [browser download provenance](../evidence/debian-vm-browser-download-provenance.json) record acquisition details. Tests ran from archive revision da9270c plus the recorded support updates; recorder and runner hashes identify executed code.

Provisioning failures on the installation-CD APT source and network/browser downloads are retained separately from successful software tests. Relevant backups and package changes are described in [engineering notes](engineering-notes.md). SSH-only operation was sufficient; no desktop environment was installed.

Additional coverage uses installed Edge 154.0.4258.37 on Windows and pinned Playwright Firefox 153.0 revision 1538 / WebKit 26.5 revision 2336 in the same Debian guest. [Archive provenance](../evidence/remaining-browser-download-provenance.json) records transfer hashes, and [adapter provenance](../evidence/remaining-browser-adapter-provenance.json) identifies the c73827a base plus source overlays. Additional libraries added 228 packages without changing existing package versions. The command-scoped HTTPS source override preserves system source content, [verified by SHA-256](../evidence/remaining-browser-source-verification.json); [final package changes](../evidence/remaining-browser-dependencies-cache.json) and failed attempts remain recorded. Playwright WebKit on Debian is not Safari verification.

The latest Debian full suite used a 43c6f57 source base plus the [readiness source overlay](../evidence/readiness-source-provenance.json), verified and backed up before applying nine files. Its recorder and runner hashes agree with the current Windows suite. No system package or browser provisioning changed during this readiness round.

## Remaining limits

Physical Linux hardware and Safari on macOS/iOS remain unverified. Application/framework contracts beyond the selected multi-module vanilla Vite starter need their own acceptance scenario. Debian installed-package execution and actual Python 3.10 source execution are now verified; required remote installed/runtime gates are pending. Timing/extraction policies establish sampled observations, not indefinitely correct output. Ordinary descendants are contained; deliberately detached/cross-OS escape is outside the contract. Novelty and maintainer usefulness still need external validation.
