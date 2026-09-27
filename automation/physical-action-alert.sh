#!/usr/bin/env bash
# =============================================================================
# physical-action-alert.sh -- "the operator is not watching the chat" alerter
#
# The operator will NOT sit in front of the Hermes window. A chat-only request
# is therefore not acceptable: every physical request must raise a REAL VISIBLE
# persistent desktop window AND a REAL AUDIBLE repeating sound, until the
# operator answers in Hermes.
#
# USAGE
#   physical-action-alert.sh start "<ACTION_ID>" "<MESSAGE>" [--title TITLE]
#                                                           [--interval SECONDS]
#   physical-action-alert.sh stop
#   physical-action-alert.sh status
#   physical-action-alert.sh test          # raises the ARMOR-X ALERT TEST gate
#
# ONLY ONE ArmorX alert may be active at a time: `start` replaces any previous
# one (and records that it did).
#
# STATE  results/runtime/physical-alert/
#   action-id  message  started-at  notifier-pid  sound-loop-pid  backend-used
#   supervisor-pid  state.json  alert.log  alert.jsonl  stop-requested
#
# POPUP BACKENDS (in order, first that works WINS and is recorded)
#   1. kdialog persistent modal dialog   (--msgbox: stays until dismissed)
#   2. zenity persistent warning/question dialog
#   3. yad (only if already available)
#   4. critical notify-send PLUS a visible Konsole alert window
# A transient notification ALONE is never sufficient; notify-send is never
# chosen while kdialog exists.
#
# AUDIO BACKENDS (in order)
#   pw-play -> paplay -> aplay -> canberra-gtk-play -> terminal bell
# The generated tone automation/armorx-alert.wav is used when present, and the
# sound is played on EVERY sink (the default sink here is HDMI, and a monitor
# without speakers must not be allowed to swallow the alert).
#
# HONESTY RULES (hard)
#   * a shell exit code of 0 is NOT evidence that the popup was visible or the
#     sound audible. Only a screenshot or the operator's own confirmation is.
#   * this script never touches the radio, the device or any device config,
#     never changes the system master volume, and never kills plasmashell,
#     unrelated notifications or unrelated dialogs.
# =============================================================================
set -uo pipefail

LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
STATE_DIR="$LAB_ROOT/results/runtime/physical-alert"
SUP_PID_FILE="$STATE_DIR/supervisor-pid"
NOTIF_PID_FILE="$STATE_DIR/notifier-pid"
SOUND_PID_FILE="$STATE_DIR/sound-loop-pid"
STATE_JSON="$STATE_DIR/state.json"
STOP_FILE="$STATE_DIR/stop-requested"
LOG="$STATE_DIR/alert.log"
JSONL="$STATE_DIR/alert.jsonl"

DEFAULT_INTERVAL=20
DEFAULT_TITLE="ARMOR-X ACTION REQUIRED"
ALERT_SOUND="${ALERT_SOUND:-$LAB_ROOT/automation/armorx-alert.wav}"
ENV_FILE="$LAB_ROOT/automation/plasma-session.env"
WRAPPER="$LAB_ROOT/automation/run-in-plasma-session.sh"
MAX_RELAUNCHES=100

mkdir -p "$STATE_DIR"

log()  { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG" >&2; }
json() { printf '%s\n' "$1" >>"$JSONL"; }

# --- session environment: always recovered from the LIVE plasma process ------
session_env() {
  if [ -x "$WRAPPER" ]; then
    "$WRAPPER" refresh-env >/dev/null 2>&1 || true
  fi
  # shellcheck disable=SC1090
  [ -f "$ENV_FILE" ] && . "$ENV_FILE"
  : "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
  if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "$XDG_RUNTIME_DIR/bus" ]; then
    DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
  fi
  export XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
  export DISPLAY="${DISPLAY:-:0}"
  export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
  export XAUTHORITY HOME USER LOGNAME PATH
}

# --- backend detection -------------------------------------------------------
popup_backend() {
  if command -v kdialog >/dev/null 2>&1; then printf 'kdialog'; return; fi
  if command -v zenity  >/dev/null 2>&1; then printf 'zenity';  return; fi
  if command -v yad     >/dev/null 2>&1; then printf 'yad';     return; fi
  if command -v notify-send >/dev/null 2>&1 && command -v konsole >/dev/null 2>&1; then
    printf 'notify+konsole'; return
  fi
  if command -v notify-send >/dev/null 2>&1; then printf 'notify-send'; return; fi
  printf 'none'
}

sound_player() {
  for m in pw-play paplay aplay canberra-gtk-play; do
    command -v "$m" >/dev/null 2>&1 && { printf '%s' "$m"; return; }
  done
  printf 'bell'
}

# --- audible alert ------------------------------------------------------------
play_sound_once() {
  local player="$1" file="$2" sinks="" s n=0
  if command -v pactl >/dev/null 2>&1; then
    sinks="$(pactl list short sinks 2>/dev/null | awk '{print $2}')"
  fi
  case "$player" in
    pw-play)
      # pw-play takes one target per invocation; hit the default plus every sink id
      [ -n "$file" ] && { pw-play "$file" >/dev/null 2>&1; }
      if command -v pactl >/dev/null 2>&1; then
        for s in $(pactl list short sinks 2>/dev/null | awk '{print $1}'); do
          [ "$s" = "0" ] && continue
          pw-play --target="$s" "$file" >/dev/null 2>&1 &
          n=$((n + 1))
        done
      fi
      ;;
    paplay)
      [ -n "$file" ] || return 0
      if [ -n "$sinks" ]; then
        while IFS= read -r s; do
          [ -n "$s" ] || continue
          paplay --volume=65536 --device="$s" "$file" >/dev/null 2>&1 &
          n=$((n + 1))
        done <<<"$sinks"
      else
        paplay --volume=65536 "$file" >/dev/null 2>&1
      fi
      ;;
    aplay)   [ -n "$file" ] && aplay -q "$file" >/dev/null 2>&1 ;;
    canberra-gtk-play) canberra-gtk-play -i alarm-clock-elapsed >/dev/null 2>&1 ;;
    bell)    printf '\a' ;;
  esac
  [ "$n" -gt 0 ] && wait 2>/dev/null
  return 0
}

# --- persistent popup --------------------------------------------------------
# Runs as its own process (notifier-pid). Blocks until the user dismisses it,
# then exits - the supervisor re-raises it, so the alert stays visible.
raise_popup_blocking() {
  local backend="$1" title="$2" body="$3"
  case "$backend" in
    kdialog)
      kdialog --title "$title" --msgbox "$body" 2>>"$STATE_DIR/popup-errors.log"
      ;;
    zenity)
      zenity --warning --title="$title" --text="$body" --width=560 2>>"$STATE_DIR/popup-errors.log"
      ;;
    yad)
      yad --title="$title" --text="$body" --center --width=560 --button=OK 2>>"$STATE_DIR/popup-errors.log"
      ;;
    notify+konsole)
      notify-send -u critical -t 0 -a "Hermes ARMOR-X lab" "$title" "$body"
      konsole -p tabtitle="$title" -e bash -lc \
        "printf '\033[1;31m%s\033[0m\n\n%s\n\nKEEP THIS WINDOW OPEN UNTIL YOU RESPOND IN HERMES\n' '$title' '$body'; exec sleep 86400" \
        >>"$STATE_DIR/popup-errors.log" 2>&1
      ;;
    notify-send)
      notify-send -u critical -t 0 -a "Hermes ARMOR-X lab" "$title" "$body"
      sleep 30
      ;;
  esac
}

# --- sub-process: sound loop (writes its own pid) ----------------------------
cmd_soundloop() {
  local interval="$1"
  printf '%s\n' "$$" >"$SOUND_PID_FILE"
  session_env
  local player file
  player="$(sound_player)"
  file=""
  [ -r "$ALERT_SOUND" ] && file="$ALERT_SOUND"
  if [ -z "$file" ]; then
    for f in /usr/share/sounds/oxygen/stereo/dialog-error-critical.ogg \
             /usr/share/sounds/freedesktop/stereo/dialog-warning.oga \
             /usr/share/sounds/alsa/Front_Center.wav; do
      [ -r "$f" ] && { file="$f"; break; }
    done
  fi
  json "$(printf '{"ts":"%s","event":"sound_loop_start","player":"%s","file":"%s","interval":%s,"pid":%s}' \
        "$(date -Is)" "$player" "$file" "$interval" "$$")"
  local i=0
  while :; do
    [ -f "$STOP_FILE" ] && break
    i=$((i + 1))
    play_sound_once "$player" "$file"
    json "$(printf '{"ts":"%s","event":"sound_played","iteration":%s,"player":"%s","file":"%s"}' \
          "$(date -Is)" "$i" "$player" "$file")"
    # interruptible sleep so `stop` is immediate
    local waited=0
    while [ "$waited" -lt "$interval" ]; do
      sleep 1
      waited=$((waited + 1))
      [ -f "$STOP_FILE" ] && { json "$(printf '{"ts":"%s","event":"sound_loop_stop","iterations":%s}' "$(date -Is)" "$i")"; return 0; }
    done
  done
  json "$(printf '{"ts":"%s","event":"sound_loop_stop","iterations":%s}' "$(date -Is)" "$i")"
  return 0
}

# --- sub-process: popup manager (writes notifier-pid) ------------------------
cmd_dialog() {
  local backend="$1" title="$2" body="$3"
  session_env
  local raises=0
  while :; do
    [ -f "$STOP_FILE" ] && break
    raises=$((raises + 1))
    [ "$raises" -gt "$MAX_RELAUNCHES" ] && { log "popup manager: giving up after $MAX_RELAUNCHES raises"; break; }
    json "$(printf '{"ts":"%s","event":"popup_raised","backend":"%s","raise_number":%s}' "$(date -Is)" "$backend" "$raises")"
    # this blocks until the operator dismisses the window
    raise_popup_blocking "$backend" "$title" "$body"
    [ -f "$STOP_FILE" ] && break
    json "$(printf '{"ts":"%s","event":"popup_dismissed_replaying","raise_number":%s}' "$(date -Is)" "$raises")"
    sleep 2
  done
  return 0
}

# --- supervisor: owns the popup manager + sound loop -------------------------
cmd_supervise() {
  local action_id="$1" title="$2" body="$3" interval="$4"
  printf '%s\n' "$$" >"$SUP_PID_FILE"
  session_env
  local backend player
  backend="$(popup_backend)"
  player="$(sound_player)"
  printf '%s\n' "$backend" >"$STATE_DIR/backend-used"
  json "$(printf '{"ts":"%s","event":"alert_start","action_id":"%s","popup_backend":"%s","sound_player":"%s","sound_file":"%s","interval":%s,"supervisor_pid":%s}' \
        "$(date -Is)" "$action_id" "$backend" "$player" "$ALERT_SOUND" "$interval" "$$")"
  log "alert start: [$action_id] popup=$backend sound=$player file=$ALERT_SOUND every ${interval}s"

  ( trap '' TERM; exec "$0" _soundloop "$interval" ) >>"$LOG" 2>&1 &
  local spid=$!
  ( trap '' TERM; exec "$0" _dialog "$backend" "$title" "$body" ) >>"$LOG" 2>&1 &
  local dpid=$!
  printf '%s\n' "$dpid" >"$NOTIF_PID_FILE"
  local n
  while :; do
    [ -f "$STOP_FILE" ] && break
    [ -f "$SUP_PID_FILE" ] || break
    # keep exactly one of each alive
    if ! kill -0 "$spid" 2>/dev/null; then
      json "$(printf '{"ts":"%s","event":"sound_loop_restart"}' "$(date -Is)")"
      ( trap '' TERM; exec "$0" _soundloop "$interval" ) >>"$LOG" 2>&1 &
      spid=$!
    fi
    if ! kill -0 "$dpid" 2>/dev/null; then
      n="$(pgrep -f "$0 _dialog" 2>/dev/null | wc -l)"
      if [ "$n" -eq 0 ]; then
        json "$(printf '{"ts":"%s","event":"popup_manager_restart"}' "$(date -Is)")"
        ( trap '' TERM; exec "$0" _dialog "$backend" "$title" "$body" ) >>"$LOG" 2>&1 &
        dpid=$!
        printf '%s\n' "$dpid" >"$NOTIF_PID_FILE"
      fi
    fi
    sleep 2
  done
  json "$(printf '{"ts":"%s","event":"alert_loop_end","action_id":"%s"}' "$(date -Is)" "$action_id")"
  log "alert loop ended for [$action_id]"
  return 0
}

# --- commands ----------------------------------------------------------------
cmd_start() {
  local action_id="" message="" interval="$DEFAULT_INTERVAL" title="$DEFAULT_TITLE"
  action_id="${1:-}"; shift || true
  message="${1:-}";   shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      --title)    title="$2";    shift 2 ;;
      --sound)    ALERT_SOUND="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  [ -n "$action_id" ] || { log "ERROR: start needs <ACTION_ID>"; exit 2; }
  [ -n "$message" ]   || { log "ERROR: start needs <MESSAGE>"; exit 2; }

  cmd_stop --quiet || true
  rm -f "$STOP_FILE"
  session_env
  printf '%s\n' "$action_id"       >"$STATE_DIR/action-id"
  printf '%s\n' "$message"         >"$STATE_DIR/message"
  printf '%s\n' "$(date -Is)"      >"$STATE_DIR/started-at"
  printf '%s\n' "$(popup_backend)" >"$STATE_DIR/backend-used"
  cat >"$STATE_JSON" <<EOF
{
 "action_id": "$action_id",
 "title": "$title",
 "message": "$message",
 "requested_at": "$(date -Is)",
 "interval_seconds": $interval,
 "popup_backend": "$(popup_backend)",
 "sound_player": "$(sound_player)",
 "sound_file": "$ALERT_SOUND",
 "state": "WAITING_FOR_PHYSICAL_ACTION"
}
EOF
  json "$(printf '{"ts":"%s","event":"alert_requested","action_id":"%s","message":"%s","interval":%s}' \
        "$(date -Is)" "$action_id" "$message" "$interval")"

  # detached supervisor -- cannot block Hermes, is a real pid we can stop
  ALERT_SOUND="$ALERT_SOUND" setsid nohup "$0" _supervise "$action_id" "$title" "$message" "$interval" \
      >>"$LOG" 2>&1 &
  local spid=$!
  printf '%s\n' "$spid" >"$SUP_PID_FILE"
  sleep 4
  if kill -0 "$spid" 2>/dev/null; then
    log "alert running: supervisor=$spid action=$action_id"
    exit 0
  fi
  log "ERROR: alert supervisor exited immediately - see $LOG"
  exit 3
}

cmd_stop() {
  local quiet=0; [ "${1:-}" = "--quiet" ] && quiet=1
  local stopped=0 pid
  touch "$STOP_FILE"
  for f in "$SUP_PID_FILE" "$SOUND_PID_FILE" "$NOTIF_PID_FILE"; do
    [ -f "$f" ] || continue
    pid="$(cat "$f" 2>/dev/null)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
      stopped=1
    fi
  done
  sleep 1
  # kill any surviving own-mode children (ours only -- matched by this script path)
  for mode in _soundloop _dialog _supervise; do
    pkill -TERM -f "$0 $mode" 2>/dev/null || true
  done
  sleep 1
  for mode in _soundloop _dialog _supervise; do
    pkill -KILL -f "$0 $mode" 2>/dev/null || true
  done
  # the visible window itself (only a kdialog/zenity/yad we raised)
  pkill -KILL -f "kdialog --title $DEFAULT_TITLE" 2>/dev/null || true
  if [ -f "$STATE_JSON" ]; then
    local aid
    aid="$(sed -n 's/.*"action_id": *"\([^"]*\)".*/\1/p' "$STATE_JSON" | head -1)"
    json "$(printf '{"ts":"%s","event":"alert_stopped","action_id":"%s","loop_stopped":%s}' "$(date -Is)" "$aid" "$stopped")"
  fi
  rm -f "$SUP_PID_FILE" "$SOUND_PID_FILE" "$NOTIF_PID_FILE" "$STATE_JSON"
  [ "$quiet" -eq 1 ] || log "alert stopped (stopped=$stopped)"
  return 0
}

cmd_status() {
  local alive_sup=false alive_dlg=false alive_snd=false
  for pair in "$SUP_PID_FILE:alive_sup" "$NOTIF_PID_FILE:alive_dlg" "$SOUND_PID_FILE:alive_snd"; do
    f="${pair%%:*}"; v="${pair##*:}"
    if [ -f "$f" ]; then
      pid="$(cat "$f" 2>/dev/null)"
      if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
        case "$v" in alive_sup) alive_sup=true ;; alive_dlg) alive_dlg=true ;; alive_snd) alive_snd=true ;; esac
      fi
    fi
  done
  if [ -f "$STATE_JSON" ]; then
    cat "$STATE_JSON"
    echo "\"supervisor_alive\": $alive_sup,"
    echo "\"notifier_alive\": $alive_dlg,"
    echo "\"sound_loop_alive\": $alive_snd,"
    if $alive_sup || $alive_dlg || $alive_snd; then
      echo "\"active_alert\": true"
    else
      echo "\"active_alert\": false"
    fi
  else
    echo '{"state": "NO_ACTIVE_ALERT", "active_alert": false}'
  fi
}

cmd_test() {
  cmd_start "alert_test" \
"ARMOR-X ALERT TEST

You should see this popup and hear a repeating alert sound.

Reply  ALERT TEST OK  in Hermes ONLY if you SAW this popup AND HEARD the sound.

If not, reply: NO POPUP / NO SOUND / NOTHING -- Hermes will troubleshoot and retry."
  rc=$?
  echo "---"
  echo "alert test requested (rc=$rc). A 0 exit code proves only that the processes started:"
  echo "it is NOT proof that the window was visible or the sound audible."
  cmd_status
}

case "${1:-}" in
  _supervise) shift; cmd_supervise "$@" ;;
  _soundloop) shift; cmd_soundloop "$@" ;;
  _dialog)    shift; cmd_dialog "$@" ;;
  start)      shift; cmd_start "$@" ;;
  stop)       shift; cmd_stop "$@" ;;
  status)     cmd_status ;;
  test)       cmd_test ;;
  *) sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
