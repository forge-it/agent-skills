FAKE_HERDR_SCRIPT = """#!/bin/bash
state_directory="${0%/*}/herdr-state"
case "$1 $2" in
  "agent get")
    status_file="$state_directory/status.$3"
    if [ ! -f "$status_file" ]; then
      echo '{"error":{"code":"agent_not_found","message":"agent target not found"}}'
      exit 1
    fi
    echo "$3" >> "$state_directory/reads.log"
    if [ -f "$state_directory/reply.raw" ]; then
      cat "$state_directory/reply.raw"
      exit 0
    fi
    status="$(cat "$status_file")"
    sequence_field=""
    if [ ! -f "$state_directory/sequence.hidden" ]; then
      sequence_field="\\"state_change_seq\\":$(cat "$state_directory/sequence.$3" 2>/dev/null || echo 0),"
    fi
    printf '{"id":"cli:agent:get","result":{"agent":{"agent":"claude","agent_status":"%s",' "$status"
    printf '"pane_id":"%s",%s"terminal_title_stripped":"Title of %s"},"type":"agent_info"}}\\n' \\
      "$3" "$sequence_field" "$3"
    ;;
  "notification show")
    if [ -f "$state_directory/notifications.fail" ]; then
      echo "simulated notification failure" >&2
      exit 1
    fi
    shift 2
    line=$(printf '%s\\t' "$@")
    echo "$line" >> "$state_directory/notifications.log"
    ;;
  *)
    exit 2
    ;;
esac
"""

NOT_TEXT_HERDR_REPLY = b"\xff\xfe\x80 this is not text"
DEEPLY_NESTED_HERDR_REPLY = b"[" * 100_000

GIT_SPY_SCRIPT = """#!/bin/bash
echo "$*" >> {calls_log}
exec {real_git} "$@"
"""

HELD_RECORD_TEMPLATE = {
    "hold_kind": "acquire",
    "herdr_session": "test-session",
    "working_directory": "/",
    "branch": "main",
    "purpose": "poached",
    "herdr_status": "working",
    "herdr_title": "",
    "idle_since": None,
    "idle_state_change_sequence": None,
}
