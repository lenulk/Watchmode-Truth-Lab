# Windows Vite experiment on 30 September 2026

This is the initial pilot evidence from commit `35ee9f1`. See [current results](current-results.md) for repaired-runner matrices, WSL2, Windows-origin mutations, and browser verification.

Vite 8.3.1 served a transformed `src/token.js` module from a temporary NTFS fixture on Windows 11. The runner mutated the source and extracted a unique token from each HTTP response. Node was v24.18.0 and Python was 3.12.14. Each configuration started a fresh Vite process and used a fresh temporary workspace and loopback port. These runs exercised server-side module freshness, not browser HMR application.

| Watcher | Mutation | Rounds passed | Median match latency | P95 match latency | Raw JSON |
| --- | --- | ---: | ---: | ---: | --- |
| Native | Overwrite | 20/20 | 94 ms | 172 ms | [report](../evidence/windows-2026-09-30/windows-native-overwrite-20.json) |
| Native | Atomic replace | 20/20 | 93.5 ms | 125 ms | [report](../evidence/windows-2026-09-30/windows-native-atomic-20.json) |
| Native | Burst | 20/20 | 93 ms | 109 ms | [report](../evidence/windows-2026-09-30/windows-native-burst-20.json) |
| Polling | Overwrite | 20/20 | 195.5 ms | 235 ms | [report](../evidence/windows-2026-09-30/windows-polling-overwrite-20.json) |
| Polling | Atomic replace | 20/20 | 93 ms | 218 ms | [report](../evidence/windows-2026-09-30/windows-polling-atomic-20.json) |
| Polling | Burst | 20/20 | 125 ms | 250 ms | [report](../evidence/windows-2026-09-30/windows-polling-burst-20.json) |

The latency starts after the final write and ends at the first matching observation, followed by a required 200 ms stable window. It includes probe scheduling and Vite work. These numbers are diagnostics for these runs, not a watcher performance benchmark. No stale output was detected here. This does not establish a test gap in Vite, and a clean result does not prove that stale output cannot occur. At the initial pilot milestone, Linux Vite, Windows-to-WSL2 edits, and browser HMR state had not yet been tested.
