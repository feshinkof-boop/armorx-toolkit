#!/usr/bin/env bash
# =============================================================================
# physical-action-alert.sh -- "the operator is not watching the chat" alerter
#
# The operator is away from the Hermes window, so a chat-only request is not
# enough: every physical request must ALSO raise a desktop popup and an audible
# sound, and keep repeating until it is acknowledged.
#
# USAGE
#   physical-action-alert.sh start "<ACTION_ID>" "<MESSAGE>" [--interval SECONDS]
#                                                   [--title TITLE] [--sound FILE]
#                                                   [--no-repeat]
#   physical-action-alert.sh stop
#   physical-action-alert.sh status
#   physical-action-alert.sh selftest        # one popup + one sound, no loop
#
# BEHAVIOUR
#   * CRITICAL-urgency desktop notification (persistent where the server allows)
#   * immediately audible sound, then notification+sound repeated every
#     --interval seconds (default 30) until `stop`
#   * exactly ONE alert loop is maintained: `start` while one is running
#     replaces it (and logs that it did)
#   * never blocks: the loop is detached, state/pid files under
#     logs/physical-action-alert/, every event appended to alert.log + alert.jsonl
#
# MECHANISM AUTO-DETECTION (nothing is assumed to exist)
#   notify : notify-send  ->  kdialog  ->  gdbus org.freedesktop.Notifications
#   sound  : paplay  ->  pw-play  ->  aplay  ->  canberra-gtk-play  ->  terminal bell
#
# SAFETY: read-only with respect to the experiment; it only makes noise. It never
#         touches the radio, the device or any config.
# =============================================================================
set -uo pipefail

LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
STATE_DIR="$LAB_ROOT/logs/physical-action-alert"
STATE_JSON="$STATE_DIR/state.json"
PID_FILE="$STATE_DIR/loop.pid"
ALERT_LOG="$STATE_DIR/alert.log"
ALERT_JSONL="$STATE_DIR/alert.jsonl"
DEFAULT_INTERVAL=30
LAST_NOTIF_SHOWN=""

mkdir -p "$STATE_DIR"

log()  { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$ALERT_LOG" >&2; }
json() { printf '%s\n' "$1" >> "$ALERT_JSONL"; }

# --- session environment: recover it from the real logged-in session ----------
session_env() {
  : "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
  if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "$XDG_RUNTIME_DIR/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
  fi
  if [ -z "${DISPLAY:-}" ]; then
    # inherit from a live graphical process of the same user
    for p in plasmashell ksmserver kwin_wayland kwin_x11; do
      pid="$(pgrep -u "$(id -u)" -x "$p" 2>/dev/null | head -1)"
      [ -n "${pid:-}" ] || continue
      for var in DISPLAY WAYLAND_DISPLAY; do
        val="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n "s/^$var=//p" | head -1)"
        [ -n "${val:-}" ] && export "$var=$val"
      done
      [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && break
    done
  fi
  : "${WAYLAND_DISPLAY:=wayland-0}"
  : "${DISPLAY:=:0}"
  export XDG_RUNTIME_DIR DISPLAY WAYLAND_DISPLAY DBUS_SESSION_BUS_ADDRESS
}

# --- mechanism detection ------------------------------------------------------
detect_notify() {
  for m in notify-send kdialog gdbus; do
    command -v "$m" >/dev/null 2>&1 && { printf '%s' "$m"; return 0; }
  done
  printf 'none'
}
detect_sound() {
  for m in paplay pw-play aplay canberra-gtk-play; do
    command -v "$m" >/dev/null 2>&1 && { printf '%s' "$m"; return 0; }
  done
  printf 'bell'
}

SOUND_CANDIDATES=(
  /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga
  /usr/share/sounds/freedesktop/stereo/dialog-warning.oga
  /usr/share/sounds/freedesktop/stereo/complete.oga
  /usr/share/sounds/Oxygen-Im-Error-On-Connection.ogg
  /usr/share/sounds/alsa/Front_Center.wav
)
pick_sound() {
  [ -n "${ALERT_SOUND:-}" ] && { printf '%s' "$ALERT_SOUND"; return; }
  for f in "${SOUND_CANDIDATES[@]}"; do
    [ -r "$f" ] && { printf '%s' "$f"; return; }
  done
  printf ''
}

play_sound() {
  local mech="$1" file="$2"
  # Play on EVERY sink, not just the default: the default here is HDMI, and a monitor with no
  # speakers would silently swallow the alert. Extra sinks cost nothing.
  local sinks=""
  if command -v pactl >/dev/null 2>&1; then
    sinks="$(pactl list short sinks 2>/dev/null | awk '{print $2}')"
  fi
  case "$mech" in
    paplay)
      [ -n "$file" ] || return 0
      if [ -n "$sinks" ]; then
        while IFS= read -r s; do
          [ -n "$s" ] || continue
          paplay --device="$s" "$file" >/dev/null 2>&1 &
        done <<< "$sinks"
        wait 2>/dev/null
      else
        paplay "$file" >/dev/null 2>&1
      fi
      ;;
    pw-play) [ -n "$file" ] && pw-play "$file" >/dev/null 2>&1 ;;
    aplay)   [ -n "$file" ] && aplay -q "$file" >/dev/null 2>&1 ;;
    canberra-gtk-play) canberra-gtk-play -i alarm-clock-elapsed >/dev/null 2>&1 ;;
    *)       printf '\a' >/dev/tty 2>/dev/null || printf '\a' ;;
  esac
  return 0
}

show_notification() {
  local mech="$1" title="$2" body="$3"
  local id=""
  case "$mech" in
    notify-send)
      # -u critical + -t 0: stays on screen until dismissed where supported
      id="$(notify-send -u critical -t 0 -a "Hermes ARMOR-X lab" -p "$title" "$body" 2>/dev/null)"
      ;;
    kdialog)
      # kdialog has no urgency knob; run it detached so it cannot block the loop
      (kdialog --title "$title" --error "$body" >/dev/null 2>&1 &) ;;
    gdbus)
      id="$(gdbus call --session --dest org.freedesktop.Notifications \
              --object-path /org/freedesktop/Notifications \
              --method org.freedesktop.Notifications.Notify \
              "Hermes ARMOR-X lab" 0 "" "$title" "$body" "[]" "{\"urgency\": <byte 2>}" 0 2>/dev/null \
              | tr -dc '0-9')"
      ;;
  esac
  LAST_NOTIF_SHOWN="$id"
}

close_notification() {
  [ -n "${LAST_NOTIF_SHOWN:-}" ] || return 0
  gdbus call --session --dest org.freedesktop.Notifications \
    --object-path /org/freedesktop/Notifications \
    --method org.freedesktop.Notifications.CloseNotification \
    "$LAST_NOTIF_SHOWN" >/dev/null 2>&1 || true
}

# --- the repeating loop (runs detached) --------------------------------------
run_loop() {
  local action_id="$1" title="$2" body="$3" interval="$4" repeat="$5"
  session_env
  local nmech smech sfile
  nmech="$(detect_notify)"; smech="$(detect_sound)"; sfile="$(pick_sound)"
  json "$(printf '{"ts":"%s","event":"alert_start","action_id":"%s","notify_mechanism":"%s","sound_mechanism":"%s","sound_file":"%s","interval":%s,"repeat":%s,"pid":%s}' \
      "$(date -Is)" "$action_id" "$nmech" "$smech" "$sfile" "$interval" "$repeat" "$$")"
  log "alert start: [$action_id] via notify=$nmech sound=$smech file=$sfile every ${interval}s"
  local i=0
  while :; do
    i=$((i + 1))
    show_notification "$nmech" "$title" "$body"
    play_sound "$smech" "$sfile"
    json "$(printf '{"ts":"%s","event":"alert_fired","action_id":"%s","iteration":%s,"notification_id":"%s"}' \
        "$(date -Is)" "$action_id" "$i" "$LAST_NOTIF_SHOWN")"
    if [ "$repeat" = "0" ]; then break; fi
    [ "$repeat" -gt 0 ] 2>/dev/null && [ "$i" -ge "$repeat" ] && break
    sleep "$interval" &
    wait $! 2>/dev/null
    # stop is signalled by removing the pid file / a stop-request file
    [ -f "$STATE_DIR/stop-requested" ] && break
    [ -f "$PID_FILE" ] || break
  done
  json "$(printf '{"ts":"%s","event":"alert_loop_end","action_id":"%s","iterations":%s}' \
      "$(date -Is)" "$action_id" "$i")"
  log "alert loop ended after $i iteration(s)"
}

# --- commands ----------------------------------------------------------------
cmd_start() {
  local action_id="" message="" interval="$DEFAULT_INTERVAL" title="ARMOR-X ACTION REQUIRED"
  local repeat=-1
  action_id="${1:-}"; shift || true
  message="${1:-}"; shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      --title)    title="$2"; shift 2 ;;
      --sound)    ALERT_SOUND="$2"; shift 2 ;;
      --no-repeat) repeat=1; shift ;;
      *) shift ;;
    esac
  done
  [ -n "$action_id" ] || { log "ERROR: start needs <ACTION_ID>"; exit 2; }
  [ -n "$message" ]   || { log "ERROR: start needs <MESSAGE>"; exit 2; }

  cmd_stop --quiet || true
  rm -f "$STATE_DIR/stop-requested"
  session_env

  # Detached loop: the script re-invokes ITSELF in `_loop` mode under setsid, so the
  # alert can never block Hermes and the loop is a real process we can kill by pid.
  ALERT_SOUND="${ALERT_SOUND:-}" setsid "$0" _loop "$action_id" "$title" "$message" \
      "$interval" "$repeat" >>"$ALERT_LOG" 2>&1 &
  local loop_pid=$!
  printf '%s\n' "$loop_pid" > "$PID_FILE"
  cat > "$STATE_JSON" <<EOF
{
 "action_id": "$action_id",
 "title": "$title",
 "message": "$message",
 "requested_at": "$(date -Is)",
 "interval_seconds": $interval,
 "repeat": $repeat,
 "loop_pid": $loop_pid,
 "notify_mechanism": "$(detect_notify)",
 "sound_mechanism": "$(detect_sound)",
 "sound_file": "$(pick_sound)",
 "state": "WAITING_FOR_PHYSICAL_ACTION"
}
EOF
  json "$(printf '{"ts":"%s","event":"alert_requested","action_id":"%s","message":"%s","interval":%s,"loop_pid":%s}' \
      "$(date -Is)" "$action_id" "$message" "$interval" "$loop_pid")"
  sleep 2
  if kill -0 "$loop_pid" 2>/dev/null; then
    log "alert running: pid=$loop_pid action=$action_id"
    exit 0
  fi
  log "ERROR: alert loop exited immediately - see $ALERT_LOG"
  exit 3
}

cmd_stop() {
  local quiet=0; [ "${1:-}" = "--quiet" ] && quiet=1
  local stopped=0 pid
  if [ -f "$PID_FILE" ]; then
    pid="$(cat "$PID_FILE" 2>/dev/null)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      # stop the loop and any child it spawned (sleep / player / notifier)
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
      sleep 1
      kill -0 "$pid" 2>/dev/null && { pkill -KILL -P "$pid" 2>/dev/null || true; kill -KILL "$pid" 2>/dev/null || true; }
      stopped=1
    fi
    rm -f "$PID_FILE"
  fi
  touch "$STATE_DIR/stop-requested"
  # close any visible persistent notification we raised
  session_env
  if [ -f "$STATE_JSON" ]; then
    LAST_NOTIF_SHOWN="$(sed -n 's/.*"notification_id"[^0-9]*\([0-9]\+\).*/\1/p' "$ALERT_JSONL" 2>/dev/null | tail -1)"
    close_notification
    local aid; aid="$(sed -n 's/.*"action_id": *"\([^"]*\)".*/\1/p' "$STATE_JSON" | head -1)"
    json "$(printf '{"ts":"%s","event":"alert_stopped","action_id":"%s","loop_stopped":%s}' \
        "$(date -Is)" "$aid" "$stopped")"
    rm -f "$STATE_JSON"
  fi
  # verify nothing of ours is left behind
  local remaining=0
  if [ -f "$ALERT_LOG" ]; then
    remaining="$(pgrep -f "physical-action-alert.sh" 2>/dev/null | grep -v "^$$\$" | wc -l)"
  fi
  [ "$quiet" -eq 1 ] || log "alert stopped (loop_stopped=$stopped, remaining_alert_procs=$remaining)"
  return 0
}

cmd_status() {
  if [ -f "$STATE_JSON" ]; then
    cat "$STATE_JSON"
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      echo "\"loop_alive\": true"
    else
      echo "\"loop_alive\": false"
    fi
  else
    echo '{"state": "NO_ACTIVE_ALERT"}'
  fi
}

cmd_selftest() {
  session_env
  local nmech smech sfile
  nmech="$(detect_notify)"; smech="$(detect_sound)"; sfile="$(pick_sound)"
  echo "notify mechanism : $nmech"
  echo "sound mechanism  : $smech"
  echo "sound file       : ${sfile:-<terminal bell>}"
  echo "DISPLAY=$DISPLAY WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
  echo "DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-<unset>} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-<unset>}"
  show_notification "$nmech" "ARMOR-X lab notification selftest" \
    "If you can see this popup AND hear a sound, the alert path works."
  echo "notification id  : ${LAST_NOTIF_SHOWN:-<none>}"
  play_sound "$smech" "$sfile"
  echo "selftest complete"
}

case "${1:-}" in
  _loop)    shift; run_loop "$@" ;;
  start)    shift; cmd_start "$@" ;;
  stop)     shift; cmd_stop "$@" ;;
  status)   cmd_status ;;
  selftest) cmd_selftest ;;
  *) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//' ; exit 2 ;;
esac
