#!/usr/bin/env bash
# operator-dialog-kdialog.sh -- ONE modal operator dialog, ONE sound, click = ACK.
#
# Prescribed by the experiment brief: prefer zenity, else kdialog. zenity is not installed here,
# so kdialog is used. The dialog is shown inside the live Plasma session (env recovered from the
# running plasmashell), plays exactly one short sound before appearing, blocks until the button is
# clicked, and records a machine-readable acknowledgement.
#
# Usage: operator-dialog-kdialog.sh --id <action_id> --title <t> --message <m> [--button LABEL]
# Exit: 0 = DONE clicked, 1 = cancelled/closed, 2 = dialog failed, 3 = GUI session unavailable
set -uo pipefail
LAB=/home/salamanka/armorx-lab
ID=""; TITLE="ArmorX Lab"; MSG=""; BTN="DONE"; CANCEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --id) ID="$2"; shift 2;;
    --title) TITLE="$2"; shift 2;;
    --message) MSG="$2"; shift 2;;
    --button) BTN="$2"; shift 2;;
    --cancel) CANCEL="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$ID" ] || { echo "missing --id" >&2; exit 2; }

# --- verify a graphical session + user D-Bus exist BEFORE asking anything ---
PLASMA_PID=$(pgrep -u salamanka plasmashell | head -1 || true)
if [ -z "${PLASMA_PID:-}" ] || [ ! -S /run/user/1000/bus ]; then
  echo "OPERATOR_UI_UNAVAILABLE" >&2
  exit 3
fi

OUTDIR="$LAB/results/runtime/operator-actions"
mkdir -p "$OUTDIR"
rm -f "$OUTDIR/$ID.json"

# --- ONE sound, then the dialog. Never looped. ---
WAV="$LAB/automation/armorx-alert.wav"
if [ -f "$WAV" ]; then
  if command -v paplay >/dev/null 2>&1; then
    "$LAB/automation/run-in-plasma-session.sh" paplay "$WAV" >/dev/null 2>&1 || true
  elif command -v pw-play >/dev/null 2>&1; then
    "$LAB/automation/run-in-plasma-session.sh" pw-play "$WAV" >/dev/null 2>&1 || true
  fi
fi

# --- the modal dialog itself (blocking until clicked) ---
# One button by default (validated contract). When a cancel label is given we use the two-button form
# so the operator always has an explicit CANCEL / STOP, as the experiment brief requires.
if [ -n "$CANCEL" ]; then
  "$LAB/automation/run-in-plasma-session.sh" kdialog --title "$TITLE" --yesno "$MSG" \
      --yes-label "$BTN" --no-label "$CANCEL"
else
  "$LAB/automation/run-in-plasma-session.sh" kdialog --title "$TITLE" --msgbox "$MSG" --ok-label "$BTN"
fi
rc=$?
now=$(date -Is)
if [ "$rc" -eq 0 ]; then
  python3 - "$OUTDIR/$ID.json" "$ID" "$TITLE" "$now" "$BTN" <<'PY'
import json, sys, os, pathlib
path, aid, title, now, btn = sys.argv[1:6]
rec = {"status": "ACK", "action_id": aid, "title": title, "response": btn.lower(),
       "clicked_at": now, "gui": "kdialog", "pid": os.getpid()}
p = pathlib.Path(path); tmp = p.with_suffix(".tmp")
tmp.write_text(json.dumps(rec, indent=1)); os.replace(tmp, p)
print(json.dumps(rec))
PY
  echo "{\"event\":\"acknowledged\",\"action_id\":\"$ID\",\"acknowledged_at\":\"$now\",\"response\":\"${BTN,,}\",\"status\":\"ACK\"}" >> "$LAB/results/runtime/operator-actions.jsonl"
  exit 0
else
  echo "{\"event\":\"cancelled\",\"action_id\":\"$ID\",\"at\":\"$now\",\"rc\":$rc}" >> "$LAB/results/runtime/operator-actions.jsonl"
  exit 1
fi
