#!/usr/bin/env bash
# =============================================================================
# request-physical-action.sh -- the single entry point for asking the operator
# to touch hardware.
#
#   request-physical-action.sh "<ACTION_ID>" "<MESSAGE>"
#
# It does ALL FOUR things, in this order, because doing fewer is how requests
# get missed:
#   1. records research state WAITING_FOR_PHYSICAL_ACTION,
#   2. raises the persistent visible popup + repeating audible alert
#      (automation/physical-action-alert.sh start, validated 2026-09-27),
#   3. prints the identical text to be pasted into Hermes chat,
#   4. leaves the alert running until `physical-action-alert.sh stop` is called
#      after the operator answers.
#
# Any autonomous step that depends on the physical action MUST stop here.
# =============================================================================
set -uo pipefail
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
ALERT="$LAB_ROOT/automation/physical-action-alert.sh"
RT="$LAB_ROOT/results/runtime/physical-alert"
STATE="$LAB_ROOT/results/runtime/research-state.json"
LOG="$LAB_ROOT/results/runtime/physical-actions.jsonl"

ACTION_ID="${1:-}"
MESSAGE="${2:-}"
TITLE="${3:-ARMOR-X ACTION REQUIRED}"
[ -n "$ACTION_ID" ] && [ -n "$MESSAGE" ] || { echo "usage: $0 <ACTION_ID> '<MESSAGE>' [TITLE]" >&2; exit 2; }
[ -x "$ALERT" ] || { echo "missing $ALERT" >&2; exit 2; }

mkdir -p "$(dirname "$STATE")" "$RT"

python3 - "$STATE" "$ACTION_ID" "$MESSAGE" <<'PY'
import json, sys, datetime, pathlib
state, aid, msg = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(state)
cur = {}
if p.exists():
    try: cur = json.loads(p.read_text())
    except Exception: cur = {}
cur.update({
  "research_state": "WAITING_FOR_PHYSICAL_ACTION",
  "pending_action_id": aid,
  "pending_message": msg,
  "requested_at": datetime.datetime.now().astimezone().isoformat(),
  "alert_system": "VALIDATED (operator confirmed ALERT TEST OK 2026-09-27)",
})
p.write_text(json.dumps(cur, indent=1) + "\n")
print("state:", cur["research_state"], "action:", aid)
PY

"$ALERT" start "$ACTION_ID" "$MESSAGE" --title "$TITLE"
rc=$?

python3 - "$LOG" "$ACTION_ID" "$MESSAGE" "$TITLE" "$rc" <<'PY'
import json, sys, datetime, pathlib
log, aid, msg, title, rc = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
with pathlib.Path(log).open("a") as f:
    f.write(json.dumps({"ts": datetime.datetime.now().astimezone().isoformat(),
                        "event": "physical_action_requested", "action_id": aid,
                        "message": msg, "title": title, "alert_rc": int(rc)}) + "\n")
PY

cat <<EOF

======================= PHYSICAL ACTION REQUIRED =======================
[ACTION_ID] $ACTION_ID
$MESSAGE

The same text is on your screen in a persistent popup and repeats audibly
every 20 seconds. Reply in Hermes when done; the alert is stopped then.
=======================================================================
EOF
exit "$rc"
