#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["click>=8.1"]
# ///
"""Watch one CI pipeline for the Monitor tool: GitLab through glab, GitHub Actions through gh.

Two output streams with two readers:

  stdout  the events the agent acts on, one line each: a blocking job failure the moment it
          lands, then the pipeline's end (PASSED / FAILED / CANCELED / SKIPPED / BLOCKED),
          or ERROR when the pipeline cannot be read any more or the script itself crashed.
          The script exits after the last one, which ends the Monitor.
  stderr  the stage board, drawn like `glab ci view` (one column per stage, one box per job,
          with durations), redrawn whenever a job changes state and, while a job runs, every
          --redraw seconds so the running times stay fresh. The Monitor's details view shows
          it, so the operator follows the progress there; the agent is not woken.

Run it with `uv run --quiet --no-project ci_watch.py ...`: the dependency block above gives
it click without touching any project's virtualenv.

Re-arming with the same command is safe at any point: the failures already reported live in
a state file under ~/.cache/ci-pipeline-watch/ (kept a week) and are not reported twice.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TextIO

import click

STATE_DIR = Path.home() / ".cache" / "ci-pipeline-watch"
STATE_MAX_AGE_S = 7 * 24 * 3600
GIVE_UP_AFTER = 10  # consecutive failed reads before the watch reports ERROR and exits
NEVER_RECOVERS = re.compile(r"HTTP 4(?!08|29)\d\d|gh auth login")  # a read that no retry will fix; 408 and 429 pass
MAX_COLUMN_WIDTH = 30  # inner width of a stage column; longer names are cut with an ellipsis
EXIT_PASSED, EXIT_NOT_PASSED, EXIT_UNREADABLE, EXIT_CRASHED = 0, 1, 3, 4

GLYPH = {
    "passed": "✔",
    "failed": "✖",
    "running": "▶",
    "waiting": "·",
    "manual": "◦",
    "skipped": "⊘",
    "canceled": "⊗",
}
ALLOWED_FAILURE_GLYPH = "!"
LEGEND = "legend  ✔ passed  ✖ failed  ! failed, allowed  ▶ running  · waiting  ◦ manual  ⊘ skipped  ⊗ canceled  ↳ child pipeline"
TERMINAL_JOB_STATES = ("passed", "failed", "skipped", "canceled")

GITLAB_JOB_STATE = {
    "success": "passed",
    "failed": "failed",
    "running": "running",
    "created": "waiting",
    "pending": "waiting",
    "waiting_for_resource": "waiting",
    "preparing": "waiting",
    "scheduled": "waiting",
    "manual": "manual",
    "skipped": "skipped",
    "canceled": "canceled",
    "canceling": "canceled",
}
GITLAB_PIPELINE_STATE = {
    "success": "passed",
    "failed": "failed",
    "canceled": "canceled",
    "skipped": "skipped",
    "manual": "blocked",
}
GITHUB_CONCLUSION_STATE = {
    "success": "passed",
    "neutral": "passed",
    "failure": "failed",
    "timed_out": "failed",
    "startup_failure": "failed",
    "cancelled": "canceled",
    "stale": "canceled",
    "skipped": "skipped",
    "action_required": "manual",
}
GITHUB_JOB_STATUS_STATE = {"in_progress": "running", "waiting": "manual"}  # waiting = a deployment approval


class FetchError(Exception):
    def __init__(self, message: str, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal


@dataclass
class Job:
    group: str  # GitLab stage, or the GitHub job name's part before " / "
    name: str
    state: str  # passed failed running waiting manual skipped canceled
    allowed: bool  # a failure here does not block the pipeline
    url: str
    key: str  # stable id, so a failure is reported once even across re-arms
    started_at: datetime | None = None
    duration_s: float | None = None


@dataclass
class Pipeline:
    title: str
    url: str
    state: str  # running passed failed canceled skipped blocked
    jobs: list[Job]
    config_error: str = ""  # GitLab's yaml_errors: why a pipeline failed before any job ran


Fetch = Callable[[str, str], Pipeline]


def never_recovers(message: str) -> bool:
    return bool(NEVER_RECOVERS.search(message)) and "rate limit" not in message.lower()


def run_json(argv: list[str]):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        raise FetchError(f"{argv[0]} is not installed or not on PATH", fatal=True) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FetchError(f"{argv[0]}: {exc}") from exc
    if done.returncode != 0:
        message = done.stderr.strip() or done.stdout.strip()
        raise FetchError(f"{' '.join(argv[:3])}: {message}", fatal=never_recovers(message))
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise FetchError(f"{' '.join(argv[:3])}: not JSON: {done.stdout[:120]!r}") from exc


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
    return parsed if parsed.year >= 2000 else None  # gh writes an unset time as 0001-01-01


# --- GitLab -----------------------------------------------------------------------------


def gitlab_pages(path: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        chunk = run_json(["glab", "api", f"{path}{sep}per_page=100&page={page}"])
        rows.extend(chunk)
        if len(chunk) < 100:
            return rows
        page += 1


def latest_attempts_in_stage_order(rows: list[dict]) -> list[dict]:
    """Keep each job's newest attempt, ordered by stage (a stage's first job id, retries included)."""
    stage_rank: dict[str, int] = {}
    latest: dict[tuple[str, str], dict] = {}
    for r in rows:
        stage_rank[r["stage"]] = min(stage_rank.get(r["stage"], r["id"]), r["id"])
        if r["id"] >= latest.get((r["stage"], r["name"]), {}).get("id", 0):
            latest[(r["stage"], r["name"])] = r
    return sorted(latest.values(), key=lambda r: (stage_rank[r["stage"]], r["id"]))


def gitlab_fetch(project: str, pipeline_id: str) -> Pipeline:
    enc = urllib.parse.quote(urllib.parse.unquote(project), safe="")  # accepts group/repo, group%2Frepo or the id
    meta = run_json(["glab", "api", f"projects/{enc}/pipelines/{pipeline_id}"])
    rows = gitlab_pages(f"projects/{enc}/pipelines/{pipeline_id}/jobs?include_retried=true")
    for bridge in gitlab_pages(f"projects/{enc}/pipelines/{pipeline_id}/bridges"):
        downstream = bridge.get("downstream_pipeline") or {}
        bridge["name"] = f"↳ {bridge['name']}"
        bridge["web_url"] = downstream.get("web_url") or bridge.get("web_url", "")
        rows.append(bridge)
    jobs = [
        Job(
            group=r["stage"],
            name=r["name"],
            state=GITLAB_JOB_STATE.get(r["status"], "waiting"),
            allowed=bool(r.get("allow_failure")),
            url=r.get("web_url", ""),
            key=str(r["id"]),
            started_at=parse_time(r.get("started_at")),
            duration_s=r.get("duration"),
        )
        for r in latest_attempts_in_stage_order(rows)
    ]
    yaml_errors = (meta.get("yaml_errors") or "").strip()
    return Pipeline(
        title=f"{project} pipeline {pipeline_id} on {meta.get('ref', '?')}",
        url=meta.get("web_url", ""),
        state=GITLAB_PIPELINE_STATE.get(meta.get("status", ""), "running"),
        jobs=jobs,
        config_error=next(iter(yaml_errors.splitlines()), "")[:160],
    )


# --- GitHub Actions ---------------------------------------------------------------------


def github_fetch(repo: str, run_id: str) -> Pipeline:
    fields = "status,conclusion,url,headBranch,workflowName,jobs"
    data = run_json(["gh", "run", "view", run_id, "-R", repo, "--json", fields])
    return github_pipeline(repo, run_id, data)


def github_pipeline(repo: str, run_id: str, data: dict) -> Pipeline:
    jobs = []
    for r in data.get("jobs", []):
        name = r.get("name", "?")
        group, _, rest = name.partition(" / ")
        status = r.get("status")
        if status == "completed":
            state = GITHUB_CONCLUSION_STATE.get(r.get("conclusion") or "", "failed")
        else:
            state = GITHUB_JOB_STATUS_STATE.get(status, "waiting")
        started = parse_time(r.get("startedAt"))
        completed = parse_time(r.get("completedAt"))
        jobs.append(
            Job(
                group=group,
                name=rest or name,
                state=state,
                allowed=False,  # gh does not expose continue-on-error; see below
                url=r.get("url", ""),
                key=str(r.get("databaseId", name)),
                started_at=started,
                duration_s=(completed - started).total_seconds() if started and completed else None,
            )
        )
    run_status = data.get("status")
    still_working = any(j.state in ("running", "waiting") for j in jobs)
    if run_status == "completed":
        state = GITHUB_CONCLUSION_STATE.get(data.get("conclusion") or "", "failed")
        state = "blocked" if state == "manual" else state
    elif run_status == "waiting" and not still_working:  # only an approval is left
        state = "blocked"
    else:
        state = "running"
    if state == "passed":  # a run that passed with failed jobs: those jobs had continue-on-error
        for job in jobs:
            if job.state == "failed":
                job.allowed = True
    return Pipeline(
        title=f"{repo} run {run_id} ({data.get('workflowName', '?')}) on {data.get('headBranch', '?')}",
        url=data.get("url", ""),
        state=state,
        jobs=jobs,
    )


# --- the board --------------------------------------------------------------------------


def grouped(jobs: list[Job], stage_order: list[str]) -> list[tuple[str, list[Job]]]:
    order: dict[str, list[Job]] = {}
    for job in jobs:
        order.setdefault(job.group, []).append(job)
    rank = {stage: i for i, stage in enumerate(stage_order)}
    return sorted(order.items(), key=lambda item: rank.get(item[0], len(rank)))


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m{total % 60:02d}s"
    return f"{total // 3600}h{(total % 3600) // 60:02d}m"


def job_glyph(job: Job) -> str:
    return ALLOWED_FAILURE_GLYPH if job.state == "failed" and job.allowed else GLYPH[job.state]


def job_status(job: Job, now_utc: datetime) -> str:
    word = "failed, allowed" if job.state == "failed" and job.allowed else job.state
    if job.state == "running" and job.started_at:
        return f"{word} {format_duration((now_utc - job.started_at).total_seconds())}"
    if job.state in TERMINAL_JOB_STATES and job.duration_s:
        return f"{word} {format_duration(job.duration_s)}"
    return word


def stage_glyph(jobs: list[Job]) -> str:
    states = {j.state for j in jobs}
    if any(j.state == "failed" and not j.allowed for j in jobs):
        return GLYPH["failed"]
    if "running" in states:
        return GLYPH["running"]
    if "waiting" in states:
        return GLYPH["waiting"]
    if "failed" in states:
        return ALLOWED_FAILURE_GLYPH
    if "canceled" in states:
        return GLYPH["canceled"]
    if "passed" in states:
        return GLYPH["passed"]
    return GLYPH["manual"] if "manual" in states else GLYPH["skipped"]


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


@dataclass
class Column:
    header: str
    boxes: list[tuple[str, str]]  # (name line, status line) per job
    inner: int = field(init=False)

    def __post_init__(self) -> None:
        longest = max([len(self.header)] + [len(line) for box in self.boxes for line in box])
        self.inner = min(longest, MAX_COLUMN_WIDTH)

    @property
    def width(self) -> int:
        return self.inner + 2

    def lines(self) -> list[str]:
        bar = "─" * self.inner
        out = [clip(self.header, self.inner).ljust(self.width), f"┌{bar}┐"]
        for i, (name, status) in enumerate(self.boxes):
            if i:
                out.append(f"├{bar}┤")
            out.append(f"│{clip(name, self.inner).ljust(self.inner)}│")
            out.append(f"│{clip(status, self.inner).ljust(self.inner)}│")
        out.append(f"└{bar}┘")
        return out


def columns(p: Pipeline, now_utc: datetime, stage_order: list[str]) -> list[Column]:
    return [
        Column(
            header=f"{stage_glyph(jobs)} {stage}",
            boxes=[(f"{job_glyph(j)} {j.name}", f"  {job_status(j, now_utc)}") for j in jobs],
        )
        for stage, jobs in grouped(p.jobs, stage_order)
    ]


def bands(cols: list[Column], width: int) -> list[list[Column]]:
    """Split the stage columns into rows of columns that fit the width."""
    rows: list[list[Column]] = [[]]
    used = 0
    for col in cols:
        needed = col.width + (1 if rows[-1] else 0)
        if rows[-1] and used + needed > width:
            rows.append([])
            used = 0
            needed = col.width
        rows[-1].append(col)
        used += needed
    return rows


def render_board(
    p: Pipeline, now: str, width: int, stage_order: list[str] | None = None, now_utc: datetime | None = None
) -> list[str]:
    now_utc = now_utc or datetime.now(timezone.utc)
    done = sum(j.state in TERMINAL_JOB_STATES for j in p.jobs)
    lines = [f"── {now}  {p.title}  {p.state}  {done}/{len(p.jobs)} done"]
    if not p.jobs:
        return lines + ["(no jobs yet)"]
    for band in bands(columns(p, now_utc, stage_order or []), width):
        rendered = [col.lines() for col in band]
        height = max((len(r) for r in rendered), default=0)
        for i in range(height):
            cells = [r[i] if i < len(r) else " " * col.width for r, col in zip(rendered, band)]
            lines.append(" ".join(cells).rstrip())
    return lines


# --- events -----------------------------------------------------------------------------


def blocking_failures(p: Pipeline) -> list[Job]:
    return [j for j in p.jobs if j.state == "failed" and not j.allowed]


def final_line(p: Pipeline) -> str:
    allowed = [f"{j.group}/{j.name}" for j in p.jobs if j.state == "failed" and j.allowed]
    blocking = [f"{j.group}/{j.name}" for j in blocking_failures(p)]
    manual = [f"{j.group}/{j.name}" for j in p.jobs if j.state == "manual" and not j.allowed]
    if p.state == "passed":
        note = f"  allowed failures: {', '.join(allowed)}" if allowed else ""
        return f"PASSED  {p.title}  {len(p.jobs)} jobs  {p.url}{note}"
    if p.state == "failed":
        cause = ", ".join(blocking) or (f"config: {p.config_error}" if p.config_error else "?")
        return f"FAILED  {p.title}  blocking: {cause}  {p.url}"
    if p.state == "blocked":
        return f"BLOCKED  {p.title}  waits on manual: {', '.join(manual) or '?'}  {p.url}"
    return f"{p.state.upper()}  {p.title}  {p.url}"


# --- state across re-arms ---------------------------------------------------------------


def state_file(provider: str, target: str, pipeline_id: str) -> Path:
    slug = urllib.parse.unquote(target).replace("/", "_")
    return STATE_DIR / f"{provider}-{slug}-{pipeline_id}.json"


def prune_state_files() -> None:
    cutoff = time.time() - STATE_MAX_AGE_S
    for path in list(STATE_DIR.glob("*.json")) + list(STATE_DIR.glob("*.tmp")):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def load_seen(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text())["seen_failed"])
    except (OSError, ValueError, KeyError):
        return set()


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")  # one temp file per watcher
    tmp.write_text(json.dumps({"seen_failed": sorted(seen)}))
    os.replace(tmp, path)  # never leave a half-written file behind


# --- main loop --------------------------------------------------------------------------


def clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


def watch(
    fetch: Fetch, provider: str, target: str, pipeline_id: str, every: int, board: TextIO, width: int, redraw: int
) -> int:
    def event(line: str) -> None:
        print(line, flush=True)

    def note(text: str) -> None:
        print(text, file=board, flush=True)

    prune_state_files()
    state_path = state_file(provider, target, pipeline_id)
    seen = load_seen(state_path)
    stage_order: list[str] = []
    last_digest = None
    last_drawn = 0.0
    failed_reads = 0

    def draw(p: Pipeline, first: bool) -> None:
        nonlocal last_drawn
        lines = ([LEGEND] if first else []) + render_board(p, clock(), width, stage_order)
        note("\n".join(lines))  # one write per board, so the harness tags it once
        last_drawn = time.monotonic()

    while True:
        try:
            p = fetch(target, pipeline_id)
        except FetchError as exc:
            failed_reads += 1
            note(f"── {clock()}  read failed ({failed_reads}/{GIVE_UP_AFTER}): {exc}")
            if failed_reads >= GIVE_UP_AFTER or exc.fatal:
                plural = "" if failed_reads == 1 else "s"
                event(f"ERROR  {provider} {target} {pipeline_id}: {exc}  (gave up after {failed_reads} read{plural})")
                return EXIT_UNREADABLE
            time.sleep(every)
            continue
        failed_reads = 0

        for stage in (j.group for j in p.jobs):
            if stage not in stage_order:
                stage_order.append(stage)
        digest = (p.state, tuple((j.group, j.name, j.state) for j in p.jobs))
        timed_running = any(j.state == "running" and j.started_at for j in p.jobs)  # the only boxes that change between reads
        if digest != last_digest or (timed_running and time.monotonic() - last_drawn >= redraw):
            draw(p, first=last_digest is None)
            last_digest = digest

        for j in blocking_failures(p):
            if j.key not in seen:
                event(f"FAILED  {j.group}/{j.name}  {j.url}")
                seen.add(j.key)
                try:
                    save_seen(state_path, seen)
                except OSError as exc:
                    note(f"── {clock()}  state not saved ({exc}): a re-arm may report this failure again")

        if p.state != "running":
            event(final_line(p))  # the state file stays: a re-arm after a partial retry must not re-report
            return EXIT_PASSED if p.state == "passed" else EXIT_NOT_PASSED

        # wait for the next read; on the way, redraw the running times whenever they are due
        wait_until = time.monotonic() + every
        while (now_m := time.monotonic()) < wait_until:
            next_redraw = last_drawn + redraw if timed_running else wait_until
            if next_redraw <= now_m:
                draw(p, first=False)
                continue
            time.sleep(min(wait_until, next_redraw) - now_m)


def run_watch(fetch: Fetch, provider: str, target: str, pipeline_id: str, **options) -> int:
    try:
        return watch(fetch, provider, target, pipeline_id, **options)
    except Exception as exc:  # noqa: BLE001 - the agent needs an ERROR line, never a silent exit
        print(f"ERROR  {provider} {target} {pipeline_id}: crashed: {exc!r}", flush=True)
        return EXIT_CRASHED


# --- command line -----------------------------------------------------------------------


def watch_options(command):
    options = (
        click.option("--every", type=click.IntRange(min=5), default=30, show_default=True, help="Seconds between polls."),
        click.option(
            "--redraw",
            type=click.IntRange(min=10),
            default=60,
            show_default=True,
            help="Seconds between board redraws while a job runs; a changed job state always redraws.",
        ),
        click.option(
            "--board",
            type=click.Choice(["stderr", "stdout"]),
            default="stderr",
            show_default=True,
            help="Stream for the stage board. stdout makes every redraw a Monitor event.",
        ),
        click.option(
            "--width",
            type=click.IntRange(min=40),
            default=100,
            show_default=True,
            help="Board width in characters; stages beyond it go to the next row.",
        ),
    )
    for option in reversed(options):  # click lists them in decoration order, innermost first
        command = option(command)
    return command


def stream(board: str) -> TextIO:
    return sys.stdout if board == "stdout" else sys.stderr


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Watch one CI pipeline: events on stdout for the agent, the stage board on stderr for the operator."""


@cli.command()
@click.argument("project")
@click.argument("pipeline_id", type=click.IntRange(min=1))
@watch_options
def gitlab(project: str, pipeline_id: int, every: int, redraw: int, board: str, width: int) -> None:
    """Watch GitLab pipeline PIPELINE_ID of PROJECT (numeric id, or the path group/repo)."""
    sys.exit(run_watch(gitlab_fetch, "gitlab", project, str(pipeline_id), every=every, board=stream(board), width=width, redraw=redraw))


@cli.command()
@click.argument("repo")
@click.argument("run_id", type=click.IntRange(min=1))
@watch_options
def github(repo: str, run_id: int, every: int, redraw: int, board: str, width: int) -> None:
    """Watch GitHub Actions run RUN_ID of REPO (owner/repo)."""
    sys.exit(run_watch(github_fetch, "github", repo, str(run_id), every=every, board=stream(board), width=width, redraw=redraw))


if __name__ == "__main__":
    cli()
