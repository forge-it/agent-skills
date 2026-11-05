"""The `status` report: what is gathered about each lock, and how it is rendered."""

import time
from dataclasses import dataclass, field
from enum import StrEnum

from agent_sync_common import HerdrStatus, format_duration

from lockctl_context import CommandContext
from lockctl_records import HoldKind
from lockctl_steal import StealPolicy
from lockctl_store import LockInspection

FREE_WITH_COMMANDS_REASON = (
    "the next `acquire`, `run` or `steal` of this lock stops these commands before it takes over, "
    "so two users never share the resource"
)


class LockState(StrEnum):
    FREE = "free"
    HELD = "held"


@dataclass
class ActivityReport:
    run_pid: int
    command: str
    running_for_seconds: float
    process_group_id: int
    orphaned: bool = False


@dataclass
class LockReport:
    lock: str
    state: LockState
    held_by_you: bool = False
    hold_kind: HoldKind = HoldKind.ACQUIRE
    owner_pid: int = 0
    holder_pid: int = 0
    pane_id: str = ""
    herdr_title: str = ""
    branch: str = ""
    scope: str = ""
    working_directory: str = ""
    purpose: str = ""
    held_for_seconds: float = 0.0
    herdr_status: HerdrStatus = HerdrStatus.UNKNOWN
    idle_for_seconds: float = 0.0
    activities: list[ActivityReport] = field(default_factory=list)
    stealable: bool = False
    reason: str = ""


def build_report(context: CommandContext, inspection: LockInspection, policy: StealPolicy) -> LockReport:
    record = inspection.record
    now = time.time()
    activities = [
        ActivityReport(
            run_pid=activity.run_pid,
            command=activity.command,
            running_for_seconds=now - activity.started_at,
            process_group_id=activity.process_group_id,
            orphaned=activity.is_orphaned,
        )
        for activity in context.store.live_activities(inspection.name)
    ]
    if not inspection.held:
        return LockReport(
            lock=inspection.name,
            state=LockState.FREE,
            activities=activities,
            reason=FREE_WITH_COMMANDS_REASON if activities else "",
        )
    if not record:
        return LockReport(
            lock=inspection.name,
            state=LockState.HELD,
            reason="the holder is starting up or stopping, or its record is stale: it cannot be judged yet",
        )

    report = LockReport(
        lock=inspection.name,
        state=LockState.HELD,
        held_by_you=context.owns(record),
        hold_kind=record.hold_kind,
        owner_pid=record.owner_pid,
        holder_pid=record.holder_pid,
        pane_id=record.pane_id,
        herdr_title=record.herdr_title,
        branch=record.branch,
        scope=record.scope,
        working_directory=record.working_directory,
        purpose=record.purpose,
        held_for_seconds=now - record.acquired_at,
        herdr_status=record.herdr_status,
        idle_for_seconds=now - record.idle_since if record.idle_since else 0.0,
        activities=activities,
    )
    if inspection.record_missing:
        report.reason = (
            "the holder's record is missing, so its state cannot be judged; "
            "its owner can `release` it, and `steal --force` frees it on the operator's word"
        )
        return report
    if report.held_by_you:
        report.reason = "held by you"
        return report

    assessment = policy.assess(record)
    report.stealable = assessment.allowed
    report.reason = assessment.reason
    if assessment.reading:
        report.herdr_status = assessment.reading.status
        report.herdr_title = assessment.reading.title or report.herdr_title
    return report


def render_report(report: LockReport) -> str:
    activity_lines = []
    for index, activity in enumerate(report.activities):
        label = "running" if not index else ""
        orphan_remark = ", the run process is gone" if activity.orphaned else ""
        activity_lines.append(
            f"  {label:<10} run pid {activity.run_pid}: {activity.command} "
            f"(for {format_duration(activity.running_for_seconds)}{orphan_remark})"
        )

    if report.state == LockState.FREE:
        if not activity_lines:
            return f"{report.lock}  free"
        header = f"{report.lock}  free, but {len(activity_lines)} command(s) still running on it"
        return "\n".join([header, *activity_lines, f"  {'note':<10} {report.reason}"])
    if not report.owner_pid:
        return f"{report.lock}  HELD\n  {report.reason}"

    title = f' "{report.herdr_title}"' if report.herdr_title else ""
    herdr_line = f"{report.herdr_status}"
    if report.idle_for_seconds and report.herdr_status.is_resting:
        herdr_line += f", idle for {format_duration(report.idle_for_seconds)}"
    process_kind = "run" if report.hold_kind == HoldKind.RUN else "holder"
    lines = [
        f"{report.lock}  HELD{' (by you)' if report.held_by_you else ''}",
        f"  holder     pane {report.pane_id or '-'}{title}"
        f" (owner pid {report.owner_pid}, {process_kind} pid {report.holder_pid})",
        f"  where      branch {report.branch or '-'}, worktree {report.scope or '-'}, "
        f"directory {report.working_directory or '-'}",
        f"  purpose    {report.purpose or '-'}",
        f"  held for   {format_duration(report.held_for_seconds)}",
        f"  herdr      {herdr_line}",
    ]
    lines.extend(activity_lines)
    lines.append(f"  stealable  {'yes' if report.stealable else 'no'}: {report.reason}")
    return "\n".join(lines)
