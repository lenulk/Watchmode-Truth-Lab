# Readiness assessment — 2026-10-01

**Acceptance reopened:** Python3.10 mutation cancellation required the product poll/sleep repair in cycle 188. The distribution below is now superseded, and its passing matrices remain historical. A new distribution and required CI must pass before release; the native snapshot enumeration repair is pending.

**1.0.0 installed acceptance passed on Windows and Debian; required hosted CI is pending.** The tool provides file/HTTP/DOM starters, preflight, diagnostics, summaries, recoverable JSON reports and reproduction arguments. Release remains blocked until the required six-job run and final evidence audit pass.

## Selected distribution

The exact wheel tested in independent fresh Windows/Debian environments is `watchmode_truth_lab-1.0.0-py3-none-any.whl`, SHA256 `5ba2eb988c391da861404a900e5a7be7ed287e664385e625dd32f91dd25fb30a`. Its sdist SHA256 is `36c914f4d83eb17caf92901b19aebc572a5d709a7c391c9120207fdd83aa2d8a`.

It was built by the successful Ubuntu Python 3.12 job in [run 36832902222](https://github.com/lenulk/Watchmode-Truth-Lab/actions/runs/36832902222) from d7100e3, artifact 11147392816. That whole run failed a separate Windows cancellation controller gate. The auxiliary repair in 3abf8d8 changes tests/scripts, not packaged code/assets; [package equivalence](../evidence/test-runs/20261001T122753Z-identity-repair-package-equivalence-3d78af.json) supports retaining the same tested distribution, subject to the new required CI.

| Gate | Observed result | Evidence |
| --- | --- | --- |
| Fresh installed console, preflight, diagnostics and file workflows | 60 updates each on Windows/Debian; imports inside fresh venv | [Windows first run](../evidence/matrices/final-selected-windows-file/first-run.json), [Debian first run](../evidence/matrices/final-selected-debian-file/first-run.json) |
| Same wheel installed HTTP | 120 updates each, independent stale control, original fixture retained | [Windows](../evidence/matrices/final-selected-windows-http/summary.json), [Debian](../evidence/matrices/final-selected-debian-http/summary.json) |
| Same wheel browser DOM/state | 120 updates per engine: Chrome, Edge, Debian Chromium/Firefox/WebKit; controls and continuity passed | [Five-engine matrix](current-results.md#installed-application-acceptance) |
| Birth-aware actual installed cancellation | Two checks each; exit 130, observed matching descendants/probes stopped | [Windows](../evidence/test-runs/20261001T122436Z-final-selected-identity-windows-cancel-d2dea5.json), [Debian](../evidence/test-runs/20261001T123310Z-final-selected-identity-debian-cancel-08ecf1.json) |
| Actual guest post-run inspection | No live executable under project-local runtime/browser storage | [Inspection](../evidence/test-runs/20261001T123436Z-final-selected-debian-process-inspection-53ea61.json) |
| Required hosted Ubuntu/Windows × Python 3.10/3.12/3.14 | New 58-test core plus installed/package/write/byte gates in progress | [Current run](https://github.com/lenulk/Watchmode-Truth-Lab/actions/runs/36862064207) |
| Owned Windows filesystem cleanup | Actual sharing/read-only boundary and persistent finalizer checks passed; Windows 3.10 passed prior CI | [Tests and repairs](test-log.md#cycle-157-nonrecursive-owned-deletion-verified-locally) |
| Generated Vite short-write policy | Controlled 120ms incomplete writes recover exact DOM, native/polling, atomic/stale controls | [Windows](../evidence/test-runs/20261001T072117Z-browser-write-boundary-repaired-fe707a.json), [Debian](../evidence/test-runs/20261001T073423Z-browser-write-boundary-debian-7926a0.json) |

Historical candidates and failed CI evidence remain retained. The old PID-only cancellation closure can adopt older unrelated processes after parent PID reuse; controlled reproduction and the repaired helpers are documented in [engineering notes](engineering-notes.md#cancellation-controller-process-creation-identity). Missing historical birth metadata prevents assigning the old CI failure a sole cause. No product cleanup defect is inferred from that assertion alone.

## Support and practical limits

- Selected multi-module vanilla Vite and dependency-accept research fixtures are verified. Other framework, route, authentication or state contracts need their own acceptance scenario. HTTP success does not establish browser HMR.
- Windows, Debian VM, hosted Ubuntu and WSL2 are distinct evidence. The last WSL2 source run explicitly skipped three unprovisioned browser tests. Physical Linux hardware and Safari on macOS/iOS remain unverified; Debian Playwright WebKit does not establish Safari.
- Generated Vite starters add a 200ms file-size stability window with 20ms checks. Native/polling modes include it. Longer interrupted writes and other watcher backends need application-specific verification; historical unfiltered fixtures are separate.
- Windows-origin mounted-storage writes in WSL2 historically stayed stale with native watching and passed with polling. UNC writes into Linux storage were a separate observation.
- Cancellation uses controlled signals in real processes, not physical keyboard events. Deliberately detached/cross-OS escape is outside ordinary-descendant containment.
- Stable samples verify the configured timing policy, not indefinite correctness. Report replacement preserves prior bytes under tested active faults, not every power/storage failure.
- No new Vite defect, upstream coverage gap or maintainer usefulness has been established. Those research criteria remain separate from practical tool acceptance.

Use the [user guide](user-guide.md), [report contract](report-format.md), [current results](current-results.md) and [test ledger](test-log.md). GitHub visibility remains private; deployment backups and failed evidence remain retained.
