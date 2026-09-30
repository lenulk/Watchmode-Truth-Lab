# Changelog

## 1.0.0 — release candidate

- Installed starters for file, Vite HTTP and browser DOM workflows, with pinned adapter dependencies and lockfile.
- Shared scenario preflight (`--validate`) without command/workspace/mutation side effects, and scenario-specific dependency/browser diagnostics (`--doctor`).
- Optional readable summary while preserving default JSON and existing invocation/exit codes.
- Recoverable report export: interrupted staging or replacement retains the previous file.
- Controlled cancellation returns 130 after ordinary process/probe cleanup.
- Generic DOM selector, independent document identity, optional interaction/retained-state checks and explicit DOM-versus-callback update metrics.
- Multi-module application starter with counter state, view and CSS.
- Wheel/sdist rebuild and isolated installed-package coverage on Windows/Debian; installed Vite/browser acceptance matrices and required CI gates.
- UTF-8 bounded Git metadata recording, source/asset provenance and retained failed evidence.

Release acceptance and GitHub verification are still in progress. See [current evidence](docs/current-results.md) and [test log](docs/test-log.md). Novelty, unspecified applications and untested hardware/platforms are not inferred from these checks.

## 0.1.0 — experimental implementation

File/HTTP freshness runner, ordinary-descendant containment, bounded output/logs, external mutations and platform/browser fixtures. Research matrices and repairs are retained in the repository.
