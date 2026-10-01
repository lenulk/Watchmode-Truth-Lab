# Readiness assessment — 2026-10-02

**1.0.0 acceptance is pending.** The current candidate is the distribution built from source `bf03c40e56e3b6387dcffdb3cbed6e1270e9e799`. Its selected wheel and sdist have passed the retained byte audit, and Windows installed file workflows have passed. The required hosted CI run and complete final environment/browser matrix are not yet accepted; no release-complete claim is made.

## Selected candidate

The exact wheel is `watchmode_truth_lab-1.0.0-py3-none-any.whl`, SHA256 `07e0cd82aa49d4a031bcf6dd72212bc0303da92eb1f14cf1426ab727d592f3da`. The sdist is `watchmode_truth_lab-1.0.0.tar.gz`, SHA256 `582c87f11e22084d73e10371126ffe5005bbe0e27fc7d9a4d4ae1df5061ce427`.

The selection receipt records successful Ubuntu Python 3.12 artifact `11182519157` from [CI run 36903993364](https://github.com/lenulk/Watchmode-Truth-Lab/actions/runs/36903993364). The retained [selection receipt](../evidence/release-acceptance-selection.json) records the wheel and sdist hashes and download provenance. That build run ended with five successful jobs and one Windows3.14 checkout-example failure. Cycles235–237 reproduced and repaired the divergent example without changing packaged inputs; a fresh required CI run and final equivalence audit remain pending.

| Gate | Current evidence | State |
| --- | --- | --- |
| Selected wheel/sdist manifest and source byte audit | [Windows byte audit, cycle 222](../evidence/test-runs/20261001T180943Z-release-acceptance-windows-byte-3cd2ab.json) | Pass |
| Installed Windows file starter, fresh import and first-run checks | [Windows file matrix](../evidence/matrices/release-acceptance-windows-file/first-run.json), [atomic replacement](../evidence/matrices/release-acceptance-windows-file/atomic_replace.json) | Pass; 20 rounds per mutation |
| Windows HTTP application scenarios and stale control | [Windows HTTP matrix](../evidence/matrices/release-acceptance-windows-http/summary.json) | Pass |
| Installed Windows Chrome and Edge browser matrices | [Chrome](../evidence/matrices/release-acceptance-windows-chrome/summary.json), [Edge](../evidence/matrices/release-acceptance-windows-edge/summary.json) | Pass |
| Installed Debian file/HTTP/Chromium matrices | Passed on the exact selected wheel; guest proofs await import | Pass reported; final audit linkage pending |
| Core suite on Windows and exact Debian source | 68-test minimum passed for each environment | Pass reported; final audit linkage pending |
| Hosted Ubuntu/Windows × Python 3.10/3.12/3.14 CI | [Run 36903993364](https://github.com/lenulk/Watchmode-Truth-Lab/actions/runs/36903993364) | Previous run failed; fresh required CI pending after checkout-example repair |
| Complete installed file/HTTP/browser matrix | Expected prefix: `release-acceptance`; see [current results](current-results.md) | Pending guest evidence import, Debian Firefox/WebKit, and remaining required gates |
| Final evidence audit | [Acceptance controller](../evidence/release_acceptance/final_acceptance_checks.py) | Pending; no acceptance receipt exists yet |

## Support and practical limits

- Selected multi-module vanilla Vite and dependency-accept research fixtures are verified. Other framework, route, authentication or state contracts need their own acceptance scenario. HTTP success does not establish browser HMR.
- Windows, Debian VM, hosted Ubuntu and WSL2 are distinct evidence. Physical Linux hardware and Safari on macOS/iOS remain unverified; Debian Playwright WebKit does not establish Safari.
- Generated Vite starters add a 200ms file-size stability window with 20ms checks. Native/polling modes include it. Longer interrupted writes and other watcher backends need application-specific verification; historical unfiltered fixtures are separate.
- Windows-origin mounted-storage writes in WSL2 historically stayed stale with native watching and passed with polling. UNC writes into Linux storage were a separate observation.
- Cancellation uses controlled signals in real processes, not physical keyboard events. Deliberately detached/cross-OS escape is outside ordinary-descendant containment.
- Stable samples verify the configured timing policy, not indefinite correctness. Report replacement preserves prior bytes under tested active faults, not every power/storage failure.
- No new Vite defect, upstream coverage gap or maintainer usefulness has been established. Those research criteria remain separate from practical tool acceptance.

Use the [user guide](user-guide.md), [scenario format](scenario-format.md), [report contract](report-format.md), [current results](current-results.md) and [test ledger](test-log.md). GitHub visibility remains private; deployment backups and failed evidence remain retained.
