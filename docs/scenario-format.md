# Scenario format

A scenario is a JSON object describing a trusted command, a copied fixture, a controlled source change, and an observable output. The runner starts the command without a shell in a temporary copy of the fixture, waits for the initial output, applies each mutation, and checks whether the expected output becomes stable.

```json
{
  "fixture_dir": "examples/fixture",
  "command": ["{python}", "{config_dir}/examples/polling_generator.py", "{workspace}/input.txt", "{workspace}/output.txt"],
  "mutation_target": "input.txt",
  "mutation": "overwrite",
  "oracle": {"type": "file", "path": "output.txt"},
  "timeout_seconds": 3,
  "probe_interval_seconds": 0.03,
  "stable_seconds": 0.1
}
```

## Required fields

- `fixture_dir`: existing directory, resolved relative to the scenario JSON file. The runner copies it for each run.
- `command`: nonempty array of strings used as argv; it is launched without a shell from the copied workspace.
- `mutation_target`: existing file inside the fixture workspace.
- `oracle`: an object describing the output to inspect.

Commands and optional `version_command` accept `{workspace}`, `{config_dir}`, `{python}`, `{node}`, and `{port}` placeholders. `{workspace}` is the temporary fixture copy. `{config_dir}` is the scenario file's directory. `{port}` is allocated for the run. The runner executes these commands, so use only commands and fixtures you trust.

## Output oracle

Set `oracle.type` to `file` with a workspace-relative `path`, or `http` with a `url` using HTTP or HTTPS. File oracle paths must stay inside the copied workspace. Without an extractor, the expected response is the mutated input bytes.

`oracle.max_output_bytes` defaults to 1 MiB and accepts values from 1 byte through 64 MiB. For transformed responses, `oracle.extract_regex` is matched against response bytes and must contain exactly one capture group; the captured bytes are compared with the expected token. HTTP reads use a disposable worker and are bounded by the observation policy.

## Mutation and expected input

`mutation` defaults to `overwrite`. The supported modes are:

- `overwrite`: write the new content to the target.
- `atomic_replace`: write a staged file and replace the target.
- `burst`: write an intermediate value, then the final value immediately.

Each round uses a unique token. Set `mutation_template` to source text with exactly one `{token}` placeholder when the token must appear inside valid source code. In that case, `initial_expected` is required and must match the fixture's initial observable value. Otherwise the initial expected value is read from `mutation_target`.

An optional `mutation_command` argv array replaces the built-in write. It accepts `{target}`, `{mode}`, `{content_base64}`, and `{intermediate_base64}` in addition to the common placeholders. `mutation_timeout_seconds` defaults to 10 seconds. A timed-out or nonzero external mutator makes the attempt inconclusive. An internal mutation I/O error is reported as `mutation_failed` and also makes the attempt inconclusive.

## Timing and environment

- `timeout_seconds` defaults to 5 and sets the post-mutation observation deadline.
- `startup_timeout_seconds` defaults to `timeout_seconds` and sets the baseline readiness deadline.
- `probe_interval_seconds` defaults to 0.05 and controls the interval between observations.
- `stable_seconds` defaults to 0.15 and is the window spanned by matching sampled observations. It must be shorter than both readiness and observation deadlines; these samples do not establish correctness between observations.
- `env` optionally maps environment variable names to string values for the watched command.
- `workspace_parent` optionally names an existing directory, relative to the scenario file (and may include `{config_dir}`), under which temporary fixture copies are created. Use it to test a particular filesystem.

`version_command` is an optional argv array whose output is recorded with the run. See the [CLI and report contract](report-format.md) for result fields, decision meanings, and exit codes. Reports may contain child-process logs and local paths; review them before sharing.
