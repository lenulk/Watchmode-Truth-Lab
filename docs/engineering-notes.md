# Engineering notes

## Windows process cleanup and console encoding

The first toy-worker test run passed but emitted `ResourceWarning` because a killed process was not waited for. The runner now waits after terminating the process tree; the focused tests finish without that warning. A CLI run also failed when a Thai workspace path was printed through a CP1252 console. The CLI now configures UTF-8 output where supported. The current Windows test pass covers both paths; Linux cleanup and other terminal encodings remain unverified.

## Vite adapter installation

The host `npm` command looked for a missing global npm CLI and could not install dependencies. The bundled pnpm CLI installed the pinned Vite version and wrote `pnpm-lock.yaml`. The first sandboxed pnpm attempt could not access the package registry; the approved network retry completed. This is an environment setup issue, not a watch-mode failure.

## WSL2 tool availability

Kali Linux is installed as a WSL2 distro and has Python 3.13.12. It does not have Node.js or pnpm. The generic Python test suite passed there, with the Vite integration test skipped. Running the Vite matrix inside WSL2 requires a Linux Node installation and Linux Vite dependencies; using Windows `node.exe` from WSL would test a Windows process instead and would not answer the Linux watcher question.
