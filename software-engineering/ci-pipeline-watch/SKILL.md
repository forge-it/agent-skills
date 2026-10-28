---
name: ci-pipeline-watch
description: >-
  Use when a CI pipeline on GitLab (glab) or GitHub Actions (gh) is running or about to run
  and its result is awaited — after a push or a merge, after a pipeline was started through
  the API, or on asks like "watch the pipeline", "monitor CI", "is it green yet", "tell me
  when it passes", "run the build and report". Also use when resuming such a watch after a
  Monitor expiry or a context compaction.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.2.0"
---

# CI Pipeline Watch

## Purpose

Watch one pipeline with one Monitor, and say only two kinds of things: a failure report for
each blocking failure, and the end result in one line. The Monitor's details view carries the
stage board, so the operator reads the progress there; progress is never reported in chat.

`scripts/ci_watch.py` keeps the two readers apart by stream: stdout holds the events you act
on, stderr holds the stage board, drawn like `glab ci view` (one column per stage, one box per
job, with durations), redrawn when a job changes state and every minute while a job runs.
The Monitor's output file holds both, stderr tagged `[stderr]`; only stdout lines reach you
as notifications.

## Resolve the pipeline

Pin the watch to the commit, never to "the latest pipeline on the branch": a later push to
that branch would be watched instead. `<project>` below is the GitLab project's numeric id or
its path with the slash encoded (`group%2Frepo`); `<group>/<repo>` is the plain path.

```bash
# GitLab
glab api "projects/<project>/pipelines?sha=<sha>" | jq -r '.[] | "\(.id) \(.status) \(.ref) \(.web_url)"'
glab api -X POST "projects/<project>/pipeline" -f ref=<branch> | jq -r '"\(.id) \(.web_url)"'   # a pipeline you start: the id is in the reply
# GitHub: one run per workflow the push triggers, each watched on its own
gh run list -R <owner>/<repo> --commit <sha> --json databaseId,workflowName,status,conclusion,url
```

An empty list right after a push means the pipeline is not created yet. Run this as a Bash
with `run_in_background: true`; it exits with the ids, or with the miss after two minutes:

```bash
for i in $(seq 8); do out=$(glab api "projects/<project>/pipelines?sha=<sha>" | jq -r '.[] | "\(.id) \(.status) \(.ref) \(.web_url)"'); [ -n "$out" ] && { echo "$out"; exit 0; }; sleep 15; done; echo "no pipeline for <sha>"; exit 1
```

GitHub: the same loop with
`out=$(gh run list -R <owner>/<repo> --commit <sha> --json databaseId,workflowName,url -q '.[] | "\(.databaseId) \(.workflowName) \(.url)"')`.

On the miss, say one line, `no pipeline started for <repo> <sha> within 2 minutes`, with the
likely reason (`[skip ci]`, CI rules that exclude the branch, no CI file), and stop.

## Arm one Monitor per pipeline

```
Monitor({
  command: "uv run --quiet --no-project ~/.claude/skills/ci-pipeline-watch/scripts/ci_watch.py gitlab <group>/<repo> <pipeline-id>",
  description: "<repo> pipeline <pipeline-id> on <ref>",
  timeout_ms: 1800000,
})
```

`github <owner>/<repo> <run-id>` watches a GitHub Actions run. `uv` is installed wherever
this skill is; the script's own dependency block gives it click, so no virtualenv is involved.
The GitLab project goes in as the plain path or the numeric id (`%2F` is accepted too).

Two pipelines are two Monitors, armed in one message; a single loop over several pipelines
sits silent on a failure until the slowest one ends. When you arm, say one line per pipeline,
`watching <repo> pipeline <id> on <ref>: <url>`, then end your turn or carry on with other
work: the events come to you. If he says the details view shows no board, arm with
`--board stdout`; board redraws then wake you too, and you send nothing for them.

The script polls every 30 seconds and exits when the pipeline ends. Its stdout lines are the
complete list of what you will receive:

| Event | When | What you do |
|---|---|---|
| `FAILED  <stage>/<job>  <job url>` | a job whose failure blocks the pipeline failed; the rest may still be running | the failure report below |
| `FAILED  <title>  blocking: <jobs>  <url>` (names the pipeline or run, carries `blocking:`) | the pipeline ended failed | the end line. When the failure report for a job in `blocking:` is not sent yet (same notification, or the investigator is still working), send no end line: that report carries `Rest of the pipeline: ended, failed`. When it says `blocking: config: …` or `blocking: ?`, no job ran: the failure report with `job config` and the pipeline url in its first line, the config text (for `?`, the run's annotations from `gh run view <run-id> -R <owner>/<repo>`) as "What failed", no investigator, and a fix that names the CI file |
| `PASSED …`, `CANCELED …`, `SKIPPED …` | the pipeline ended | the end line |
| `BLOCKED  <title>  waits on manual: <jobs>  <url>` | the pipeline waits for a manual job, or a GitHub deployment approval | the end line, naming the job to click |
| `ERROR …` | the pipeline could not be read (ten failed reads, a 401/403/404, glab or gh missing), or the script crashed (`crashed:`) | a crash gets one line with its text. A 404 is a wrong project or id: resolve again from the sha and arm once more; a second 404 gets one line with both ids tried. Anything else: one line with the error text and the command that fixes it (for example `glab auth login`) |
| the Monitor's expiry notice | the pipeline outlived the 30 minutes | arm the same command again, no message: the script remembers for a week which failures it already reported |

A GitLab job allowed to fail shows `!` on the board, appears in the `PASSED` line's
`allowed failures:`, and emits no event. On GitHub the script cannot see `continue-on-error`
while the run is going: before reporting a `FAILED` job there, check that job in the
workflow file; when it has `continue-on-error: true`, send nothing now. A GitHub run that
ends passed lists its failed jobs as `allowed failures:` on its own.
GitHub has no stages: the board groups jobs by the part of the name before ` / ` (the calling
workflow, or the job itself, so a job event then reads `<job>/<job>`), and its titles say
`run`, not `pipeline`.

**Arm the same command again, with no message,** when the Monitor expired; when he started
the manual job named in a `BLOCKED` line; when you or he retried a job after the pipeline had
ended (GitLab keeps the pipeline id, `gh run rerun` keeps the run id). While the pipeline still
runs, the watcher follows a retry on its own. A Monitor that exits (not expires) without
having sent an end line (`PASSED`, `FAILED <title>`, `CANCELED`, `SKIPPED`, `BLOCKED` or
`ERROR`) has crashed: read its output file and send its last line, in one line.

**Resuming after a compaction.** Monitors keep running through it. Arm again only a pipeline
whose Monitor you saw end (expiry notice or exit) without an end line. Unsure whether one is
still running: `TaskStop` it by its task id before arming; two watchers on one pipeline
report each new failure twice.

## What you say

Your chat messages about a pipeline are exactly the lines this skill names: the arming line,
the no-pipeline line, the failure reports, the end line (or the chain's end message), the
`ERROR` line and the crash line. The board is his to read.

**The end line**, one line: `<repo> pipeline <id> on <ref> <passed|failed|canceled|skipped|blocked> · <url>`,
then `allowed failures: …`, `blocking: …` or `waits on: …` copied from the event when it
carried one. When the pipeline is one step of a chain (push → pipeline → appliance build →
message the developer), act on its pass without a message: start the next step and arm its
Monitor, with no arming line. The chain's single end message names every pipeline that passed, with urls. A
failure at any step gets the failure report.

**The failure report.** Start at once, send once. Read the log with the commands below;
dispatch the issue investigator for the job's language (`python-`, `react-`, `vue-` or
`rust-issue-investigator`), briefed with the job url, the quoted lines, and the job's
`script:` from the CI file as the command that reproduces it; send the report when it
returns. A job with no code behind its failure (a runner, registry or network error) gets no
investigator: the log is the evidence. A second `FAILED` job that lands before you send goes
into the same report; one that lands after gets its own. After the report, wait for his pick;
the Monitor keeps running, and the end line follows when it arrives.

```
Blocking failure: <repo> pipeline <id> on <ref>, job <stage>/<job>  <job url>
What failed: 2–6 lines quoted from the log: the assertion or the error, not the output around it
Cause: one sentence: what the investigator found, or what was ruled out and what is still open
Fix, recommended first:
1. <the change, with the file> — why it is the right one
2. <an alternative> — when it would be preferred
3. <retry or rerun> — only when the log shows a flake or an outage, with that evidence
Rest of the pipeline: still running | ended, <status>
```

With two or more jobs, repeat the first three lines (`Blocking failure`, `What failed`,
`Cause`) per job, then one `Fix` list covering them, then one `Rest of the pipeline`.

A job event of the form `FAILED  <stage>/↳ <name>  <url>` is a child pipeline, and its url
is that pipeline's page, `…/<group>/<repo>/-/pipelines/<id>`: take the project (the path
before `/-/`) and the id from it, arm a second Monitor on it with the same script, and write
the report from that pipeline's failing job.

## Reading the failure

```bash
glab api "projects/<project>/jobs/<job-id>/trace" | tail -120          # <job-id>: the last number of the job url
glab api "projects/<project>/pipelines/<pipeline-id>/test_report" | jq -r '.test_suites[].test_cases[] | select(.status=="failed" or .status=="error") | "\(.classname)\n\(.system_output)"'
gh run view <run-id> -R <owner>/<repo> --log-failed | tail -120
```

When the job publishes a JUnit report, read it first: a test job's trace often ends in
warnings printed after the real failure. When the report is empty, read the trace.

## Common mistakes

- One combined loop over several pipelines, or a `run_in_background` Bash that exits only at
  the end: a failure stays hidden until everything finishes.
- Resolving the pipeline by branch instead of by commit.
- Reporting a GitHub `continue-on-error` job as a blocking failure.
- Reading a `↳` job's url as a job id.
