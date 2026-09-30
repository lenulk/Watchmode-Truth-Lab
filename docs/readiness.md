# Readiness assessment — 2026-10-01

**Ready for a local experimental pilot within the verified environments.** The current regression gates pass after repairing three product issues found during this review: HTTP worker starvation, uncontrolled report-write errors, and an incompatible minimum build backend. The stale-file startup policy and package test harness also required corrections. This is not evidence of absence of every bug or production readiness for every application.

| Current gate | Result | Evidence |
| --- | --- | --- |
| Windows Python 3.12.14 complete suite, including real Chrome/Vite and failure cases | 30 passed; zero skips | [Suite](../evidence/test-runs/20260930T192901Z-readiness-windows-repaired-78db90.json) |
| Debian 12.15 VMware Python 3.11.2 complete suite, including real Chromium/Vite | 30 passed; zero skips | [Suite](../evidence/test-runs/20260930T193050Z-readiness-debian-full-c6c072.json) |
| Actual Debian project-local runtime/browser process cleanup | Passed | [Inspection](../evidence/test-runs/20260930T193151Z-readiness-debian-cleanup-151fc2.json) |
| Windows wheel built with exact minimum setuptools 77.0.3; installed console outside checkout | Passed: license/modules, file/report, slow HTTP, invalid input | [Package check](../evidence/test-runs/20260930T191902Z-installed-package-complete-df4c90.json) |
| Windows Vite repeated HTTP observations after repair | 120 positive updates passed; disabled watcher correctly stale | [Matrix](../evidence/matrices/windows-readiness-http-2026-10-01/summary.json) |
| Retained evidence and documentation audit | Three checks passed: JSON/summary consistency, links, home-path redaction | [Audit](../evidence/test-runs/20260930T193842Z-readiness-artifact-audit-4d2039.json) |

The Debian source was deployed only after SHA-256 verification and backup of prior files; [overlay provenance](../evidence/readiness-source-provenance.json) identifies the archive base and each updated file. Windows and Debian suite records have the same runner hash. Every failed and passing cycle, its analysis and follow-up is retained in [the test log](test-log.md). Additional Chrome/Edge/Firefox/WebKit and WSL2 evidence in [current results](current-results.md) predates this HTTP repair and is identified separately.

## Limits and next meaningful validation

- Use a scenario-specific oracle and timing policy for the intended application. Current browser fixtures cover dependency-accept HMR; application-specific workflows remain unverified.
- Physical Linux hardware and Safari on macOS/iOS have not been tested. Debian VM and Playwright WebKit results do not establish those environments.
- Python 3.10 is the declared runtime floor; actual current full suites used 3.11 and 3.12. Linux installed-wheel execution remains untested.
- Windows-origin writes to mounted Windows storage in WSL2 previously stayed stale with native watching and passed with polling, matching the documented limitation. UNC writes to Linux storage were a separate successful experiment.
- Stable samples establish the configured observation policy, not continuous correctness. Deliberately detached/cross-OS process escape is outside ordinary-descendant containment.
- No new Vite defect or gap in its existing tests has been established. The project's research go/no-go criterion and maintainer usefulness still need external validation. Nothing was published during this review.

The next useful validation is the intended application's actual scenario, or a specifically required environment above. Repeating unchanged suites alone does not resolve these limits.
