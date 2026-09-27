#!/usr/bin/env bash
# =============================================================================
# close-press-group.sh -- one operator reply = stop the alert + record the
# acknowledgement + attribute the captured frames in that window.
#
# Usage: close-press-group.sh <ACTION_ID> <REQUESTED_ISO> <BUTTON...>
#
# Everything is appended to results/runtime/press-groups.jsonl so the key-ID map
# can be rebuilt from raw evidence at any time.
# =============================================================================
set -uo pipefail
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
ACTION="${1:?usage: close-press-group.sh <ACTION_ID> <REQUESTED_ISO> <BUTTON...>}"
REQ="${2:?usage: close-press-group.sh <ACTION_ID> <REQUESTED_ISO> <BUTTON...>}"
shift 2
BUTTONS=("$@")
D2="$(cat "$LAB_ROOT/results/runtime/d2-session-path.txt")"
ACK="$(date -Is)"

"$LAB_ROOT/automation/physical-action-alert.sh" stop >/dev/null 2>&1

python3 - "$LAB_ROOT/results/runtime/press-groups.jsonl" "$ACTION" "$REQ" "$ACK" "${BUTTONS[@]}" <<'PY'
import json, sys, pathlib
log, action, req, ack = sys.argv[1:5]
buttons = sys.argv[5:]
with pathlib.Path(log).open("a") as f:
    f.write(json.dumps({"action_id": action, "requested_timestamp": req,
                        "acknowledged_timestamp": ack, "operator_response": "done",
                        "requested_buttons": buttons, "expected_order": True}) + "\n")
print(f"ack recorded: {action} {req} -> {ack}")
PY

python3 "$LAB_ROOT/automation/scripts/attribute-presses.py" "$D2/session.jsonl" \
  --from "$REQ" --to "$ACK" --expect "${BUTTONS[@]}" \
  --json-out "$LAB_ROOT/$(dirname "$D2")/$(basename "$D2")/observations/${ACTION}.json"
echo "attribution rc=$?"
