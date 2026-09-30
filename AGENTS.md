# Watchmode Truth Lab working rules

- Read the current Git state and `docs/test-log.md` before a new test or repair cycle.
- Run automated tests through `scripts/test_cycle.py` so each execution saves JSON results and a text log under `evidence/test-runs/`, including failures and skips.
- Run experimental scenarios with `--report` and retain reports used to support a conclusion under `evidence/`.
- After each cycle, add an entry to `docs/test-log.md` stating the purpose, result, analysis, change made, and remaining limitation. Fix one principal issue per repair cycle and queue other findings.
- Verify failures with controlled fixtures before changing the runner. Include a deliberately stale control when evaluating a real-tool adapter.
- Distinguish unit simulation, generic integration tests, real-tool verification, WSL2 Linux-side edits, Windows-to-WSL2 edits, and browser HMR verification.
- Identify Debian VM verification separately from WSL2 and physical Linux hardware. Record provisioning failures separately from software tests, preserving relevant backups and rollback references.
- Do not describe a clean test run as proof that no bugs remain. Do not publish a discovered gap as a new tool bug until supported-workflow behavior and existing coverage have been checked.
