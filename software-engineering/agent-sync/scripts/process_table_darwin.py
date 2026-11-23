"""The macOS counterpart of /proc/<pid>/stat for agent_sync_common: libproc says what the kernel knows of
a pid and of a process group, and sysctl says how a process was launched. Both are reached through ctypes,
so nothing is installed. libproc is loaded on the first call, so this module imports on any platform, and
it imports nothing of agent-sync, so agent_sync_common can import it without a cycle."""

import ctypes
import errno
import os
import sys
from dataclasses import dataclass
from enum import IntEnum
from functools import cache
from pathlib import PurePosixPath

LIBPROC_PATH = "/usr/lib/libproc.dylib"
LIBSYSTEM_PATH = "/usr/lib/libSystem.B.dylib"
PROC_PIDTBSDINFO = 3
PROC_PGRP_ONLY = 2
INCLUDE_ZOMBIES = 1
CTL_KERN = 1
KERN_PROCARGS2 = 49
SYSCTL_NAME_LENGTH = 3
MAX_PID = 2**31 - 1
INT_BYTES = ctypes.sizeof(ctypes.c_int)
SPARE_PID_SLOTS = 64
MICROSECONDS_PER_SECOND = 1_000_000
COMMAND_NAME_BYTES = 16
PROCESS_NAME_BYTES = 32


class ProcessStatus(IntEnum):
    """`pbi_status`: the SIDL to SZOMB values of sys/proc.h."""

    IDLE = 1
    RUNNING = 2
    SLEEPING = 3
    STOPPED = 4
    ZOMBIE = 5


class BsdInfo(ctypes.Structure):
    """`struct proc_bsdinfo` of sys/proc_info.h, 136 bytes. Its layout is the contract with the kernel,
    so every field is declared under its header name, including the ones nobody reads."""

    _fields_ = (
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * COMMAND_NAME_BYTES),
        ("pbi_name", ctypes.c_char * PROCESS_NAME_BYTES),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    )


@dataclass(frozen=True)
class LibprocProcess:
    """What libproc says about a process, reduced to what agent-sync compares. `start_microseconds`
    only ever answers "is this the same process as before", so its unit does not matter to callers."""

    command_name: str
    status: int
    parent_pid: int
    process_group_id: int
    start_microseconds: int


@cache
def load_libproc() -> ctypes.CDLL:
    libproc = ctypes.CDLL(LIBPROC_PATH, use_errno=True)
    libproc.proc_pidinfo.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int)
    libproc.proc_pidinfo.restype = ctypes.c_int
    libproc.proc_listpids.argtypes = (ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int)
    libproc.proc_listpids.restype = ctypes.c_int
    return libproc


@cache
def load_libsystem() -> ctypes.CDLL:
    libsystem = ctypes.CDLL(LIBSYSTEM_PATH, use_errno=True)
    libsystem.sysctl.argtypes = (
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
        ctypes.c_size_t,
    )
    libsystem.sysctl.restype = ctypes.c_int
    return libsystem


def build_call_error(call: str) -> OSError:
    """The OSError for the system call that just failed. The constructor turns EPERM into
    PermissionError and ESRCH into ProcessLookupError, so callers can catch the kind they expect."""
    error_number = ctypes.get_errno() or errno.EIO
    return OSError(error_number, f"{call}: {os.strerror(error_number)}")


def read_libproc_process(pid: int) -> LibprocProcess | None:
    """None when the process is gone. A failure for any other reason raises: libproc refuses to describe
    a process of another user (EPERM), which says nothing about whether it lives. Zombies are asked for
    explicitly, because `proc_pidinfo` otherwise answers ESRCH for a process that exited and is not
    reaped yet, and callers must tell that apart from a process that is gone. A pid outside the 32-bit
    range is gone too: ctypes would wrap it into the pid of some unrelated process."""
    if not 0 <= pid <= MAX_PID:
        return None

    info = BsdInfo()
    ctypes.set_errno(0)
    answer_bytes = load_libproc().proc_pidinfo(
        pid, PROC_PIDTBSDINFO, INCLUDE_ZOMBIES, ctypes.byref(info), ctypes.sizeof(info)
    )
    if answer_bytes != ctypes.sizeof(info):
        if ctypes.get_errno() == errno.ESRCH:
            return None
        raise build_call_error(f"proc_pidinfo({pid})")

    return LibprocProcess(
        command_name=info.pbi_comm.decode(errors="replace"),
        status=info.pbi_status,
        parent_pid=info.pbi_ppid,
        process_group_id=info.pbi_pgid,
        start_microseconds=info.pbi_start_tvsec * MICROSECONDS_PER_SECOND + info.pbi_start_tvusec,
    )


def list_libproc_group_pids(group_id: int) -> list[int]:
    """The pids libproc lists in a process group, zombies included: telling them apart is the caller's
    job, which reads each pid anyway. The size question is answered for every process of the machine, so
    the spare slots only matter when processes start between the two calls; the loop covers the rest."""
    if not 0 <= group_id <= MAX_PID:
        return []

    libproc = load_libproc()
    while True:
        ctypes.set_errno(0)
        needed_bytes = libproc.proc_listpids(PROC_PGRP_ONLY, group_id, None, 0)
        if needed_bytes < 0:
            raise build_call_error(f"proc_listpids(group {group_id})")
        pids = (ctypes.c_int * (needed_bytes // INT_BYTES + SPARE_PID_SLOTS))()
        ctypes.set_errno(0)
        answer_bytes = libproc.proc_listpids(PROC_PGRP_ONLY, group_id, pids, ctypes.sizeof(pids))
        if answer_bytes < 0:
            raise build_call_error(f"proc_listpids(group {group_id})")
        if answer_bytes < ctypes.sizeof(pids):
            return [pid for pid in pids[: answer_bytes // INT_BYTES] if pid > 0]


def read_launch_arguments(pid: int) -> bytes:
    """KERN_PROCARGS2 of the process: the arguments the kernel saved when it was executed. Raises
    OSError when they cannot be read: EINVAL for a zombie or a pid that is gone, EPERM for a process of
    another user."""
    sysctl_name = (ctypes.c_int * SYSCTL_NAME_LENGTH)(CTL_KERN, KERN_PROCARGS2, pid)
    libsystem = load_libsystem()

    needed_bytes = ctypes.c_size_t(0)
    ctypes.set_errno(0)
    if libsystem.sysctl(sysctl_name, SYSCTL_NAME_LENGTH, None, ctypes.byref(needed_bytes), None, 0):
        raise build_call_error(f"sysctl(KERN_PROCARGS2, {pid})")

    buffer = ctypes.create_string_buffer(needed_bytes.value)
    filled_bytes = ctypes.c_size_t(needed_bytes.value)
    ctypes.set_errno(0)
    if libsystem.sysctl(sysctl_name, SYSCTL_NAME_LENGTH, buffer, ctypes.byref(filled_bytes), None, 0):
        raise build_call_error(f"sysctl(KERN_PROCARGS2, {pid})")
    return buffer.raw[: filled_bytes.value]


def parse_launch_names(launch_arguments: bytes) -> tuple[str, ...]:
    """The basenames of the path a process was executed from and of its argv[0]. KERN_PROCARGS2 holds
    an int argc, that path, NUL padding, then argv and the environment, each NUL-terminated.
    The kernel names a process after the file it executed, so a symlink `claude` to a versioned binary
    runs as `2.1.316`; the path and argv[0] still carry the name the process was started under."""
    argument_count = int.from_bytes(launch_arguments[:INT_BYTES], sys.byteorder)
    executed_path, _, after_path = launch_arguments[INT_BYTES:].partition(b"\0")
    first_argument = after_path.lstrip(b"\0").partition(b"\0")[0] if argument_count else b""
    return tuple(
        PurePosixPath(raw_path.decode(errors="replace")).name
        for raw_path in (executed_path, first_argument)
        if raw_path
    )
