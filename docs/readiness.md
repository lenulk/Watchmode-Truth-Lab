# Readiness assessment — 2026-10-01

**1.0.0 release candidate: installed workflows verified; required remote acceptance in progress.** The tool supplies file/HTTP/DOM starters, preflight, diagnostics, readable summaries, recoverable JSON reports and reproduction arguments. Release acceptance requires all six actual CI jobs and selected distribution verification.

| Gate | Observed result | Evidence |
| --- | --- | --- |
| Windows/Debian revised source before additive report fields | 46/46 each, zero skips | [Windows](../evidence/test-runs/20260930T215533Z-release-r2-source-windows-84113d.json), [Debian](../evidence/test-runs/20260930T215740Z-release-r2-source-debian-6cfaf8.json) |
| Current reproduction/report compatibility | Six targeted checks per platform, actual quoted invocation | [PowerShell](../evidence/test-runs/20260930T220119Z-reproduction-filename-after-ac56b2.json), [POSIX](../evidence/test-runs/20260930T220715Z-reproduction-posix-debian-239ba2.json) |
| Minimum-backend wheel/sdist rebuild and installed starters/versions/reproduction | Passed outside checkout, all three starters | [Current package](../evidence/test-runs/20260930T220700Z-release-reproduction-package-utf8-ecc3f9.json), [Debian before additive reproduction](../evidence/test-runs/20260930T214511Z-release-package-debian-643e08.json) |
| Independent installed HTTP and multi-module stateful DOM workflows | 120 positives per engine/workflow plus expected-stale control | [Installed support matrix](current-results.md#installed-application-acceptance) |
| Installed controlled cancellation in startup, HTTP, mutation and live browser | Exit 130; observed ordinary descendants/probes stopped | [Windows mutation](../evidence/test-runs/20260930T215300Z-installed-cancel-mutation-repaired-85bba3.json), [Windows browser](../evidence/test-runs/20260930T215430Z-installed-browser-cancel-windows-993007.json), [Debian](../evidence/test-runs/20260930T215955Z-release-r2-debian-cancel-a61a5a.json) |
| Actual guest post-experiment process inspection | No live project-local runtime/browser executable | [Inspection](../evidence/test-runs/20261001T064719Z-release-debian-final-process-inspection-ff66fe.json) |
| Required GitHub Windows/Linux Python 3.10/3.12/3.14 | Second run: all Ubuntu gates passed; Windows sharing/empty-DOM failures retained. Repairs verified locally, remote repeat pending | [Second run](https://github.com/lenulk/Watchmode-Truth-Lab/actions/runs/36826538842), [job results](../evidence/ci/run-36826538842/jobs.json) |
| Owned Windows workspace sharing boundary | Actual non-delete-shared handle and bounded failure checks passed | [Cycle 147](../evidence/test-runs/20261001T070947Z-workspace-sharing-lock-repaired-782a87.json) |
| Generated starter short-write policy | Native/polling controlled 120ms incomplete writes recover exact DOM without empty token; atomic and stale controls passed | [Cycle 149](../evidence/test-runs/20261001T072117Z-browser-write-boundary-repaired-fe707a.json) |

Candidates changed during diagnostics/cancellation/reproduction repairs. Every matrix identifies its tested artifact; unchanged browser assets do not establish byte-identical final-artifact execution. CI builds one wheel/sdist pair per job, installs its wheel outside the checkout and runs actual HTTP/stateful DOM/cancellation acceptance. The release must identify the selected passed artifact's checksums. No release is yet declared accepted here.

## Support and practical limits

- Adapt the fixture/oracle/timing policy to the intended application. Selected multi-module vanilla Vite state and dependency-accept fixtures are verified; other framework, route or state contracts need their own acceptance.
- Windows, Debian VM, hosted Linux and WSL2 are distinct evidence. Current WSL2 source has three explicit unprovisioned-browser skips. Physical Linux hardware and Safari on macOS/iOS are unverified; Debian Playwright WebKit does not establish Safari.
- Required CI rejects skipped, empty, failed or wrong-revision records. First-run Windows source errors lost case detail because artifact naming was broken; the second run retained sharing violations, but did not identify the handle holder.
- Generated Vite starters add a 200ms file-size stability window with 20ms checks. Native/polling modes include it; historical unfiltered scenarios are separate. Longer interrupted writes and other watcher backends require application-specific verification.
- Historical Windows-origin writes to mounted Windows storage in WSL2 stayed stale with native watching and passed with polling. UNC writes into Linux storage were a separate observation.
- Cancellation signals are self-delivered in real processes, not physical keyboard events. Deliberately detached/cross-OS escape is outside ordinary-descendant containment.
- Stable samples establish the configured policy, not continuous/indefinite correctness. Report replacement preserves prior bytes under tested active faults, not every power/storage failure.
- No new Vite defect, upstream coverage gap or maintainer usefulness has been established. That research criterion is separate from this usable tool's acceptance.

Use the [user guide](user-guide.md), [report contract](report-format.md) and [test ledger](test-log.md). Failed evidence/deployment backups are retained and private GitHub visibility is preserved.
