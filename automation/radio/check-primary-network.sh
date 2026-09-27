#!/usr/bin/env bash
# =============================================================================
# check-primary-network.sh
#
# Verify that this machine's PRIMARY network (default: wlp3s0, the internal
# Qualcomm ath12k Wi-Fi that carries the default route) is still associated and
# still owns the default route -- and optionally that nothing has changed
# versus a stored baseline snapshot.
#
# USAGE
#   check-primary-network.sh [-h|--help]
#   check-primary-network.sh [--snapshot] [--quiet] [--compare-with <file>]
#
#   (no options)         verify + print the canonical snapshot.
#   --snapshot           print the canonical snapshot to stdout and exit 0.
#   --compare-with FILE  verify, then fail if the canonical snapshot differs
#                        from the one stored in FILE (unified diff is printed).
#   --quiet              suppress the snapshot dump; only PASS/FAIL lines.
#
#   Environment: PRIMARY_IF (default wlp3s0)
#
# EXIT CODES
#   0  primary network healthy (and unchanged, if --compare-with was used)
#   1  verification failed (not associated / no default route / changed)
#   2  usage or prerequisite error
#
# SAFETY: strictly read-only. This script never runs `rfkill block`,
#         never loads/unloads a driver and never changes any interface.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
PRIMARY_IF="${PRIMARY_IF:-wlp3s0}"

die()  { printf '%s: ERROR: %s\n' "$SELF" "$*" >&2; exit 2; }
fail() { printf '%s: FAIL: %s\n'  "$SELF" "$*" >&2; exit 1; }
ok()   { printf '%s: PASS: %s\n'  "$SELF" "$*"; }

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

COMPARE_WITH=""
SNAPSHOT_ONLY=0
QUIET=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --snapshot) SNAPSHOT_ONLY=1 ;;
    --quiet) QUIET=1 ;;
    --compare-with) shift; [ -n "${1:-}" ] || die "--compare-with needs a file argument"; COMPARE_WITH="$1" ;;
    --compare-with=*) COMPARE_WITH="${1#*=}" ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

command -v ip >/dev/null 2>&1 || die "required command not found: ip"

# --- canonical snapshot ------------------------------------------------------
# Only *stable* fields are emitted. Volatile counters (signal, bitrate, RX/TX
# byte counters, urbnum) are deliberately excluded so that --compare-with does
# not flap while the link is healthy.
snapshot() {
  local ifn="$PRIMARY_IF" mac mtu oper a4 a6 ssid bssid freq
  local ddev dgw dmetric dsrc nmstate nmdev nmconn

  [ -e "/sys/class/net/$ifn" ] || return 1

  mac=$(cat "/sys/class/net/$ifn/address" 2>/dev/null)
  mtu=$(cat "/sys/class/net/$ifn/mtu" 2>/dev/null)
  oper=$(cat "/sys/class/net/$ifn/operstate" 2>/dev/null)
  a4=$(ip -4 -o addr show dev "$ifn" scope global 2>/dev/null | awk '{print $4}' | sort | paste -sd, -)
  a6=$(ip -6 -o addr show dev "$ifn" 2>/dev/null | awk '{print $4}' | sort | paste -sd, -)

  if command -v iw >/dev/null 2>&1; then
    ssid=$(iw dev "$ifn" link 2>/dev/null | awk -F': ' '/^\tSSID:/{print $2}' | sed 's/[[:space:]]*$//')
    bssid=$(iw dev "$ifn" link 2>/dev/null | awk '/Connected to/{print $3}')
    freq=$(iw dev "$ifn" link 2>/dev/null | awk -F': ' '/^\tfreq:/{print $2}')
  fi
  ssid=${ssid-}; bssid=${bssid-}; freq=${freq-}

  read -r ddev dgw dmetric dsrc < <(
    ip route show default 2>/dev/null | awk '
      {dev=""; gw=""; met=""; src="";
       for(i=1;i<=NF;i++){
         if($i=="dev") dev=$(i+1);
         if($i=="via") gw=$(i+1);
         if($i=="metric") met=$(i+1);
         if($i=="src") src=$(i+1)
       }
       print dev, gw, met, src; exit}'
  )
  ddev=${ddev-}; dgw=${dgw-}; dmetric=${dmetric-}; dsrc=${dsrc-}

  if command -v nmcli >/dev/null 2>&1; then
    nmstate=$(nmcli -t -g STATE general status 2>/dev/null | head -n1)
    nmdev=$(nmcli -t -g GENERAL.STATE device show "$ifn" 2>/dev/null | head -n1 | sed 's/ (.*//')
    nmconn=$(nmcli -t -g GENERAL.CONNECTION device show "$ifn" 2>/dev/null | head -n1)
  fi

  printf 'iface.name=%s\n'            "$ifn"
  printf 'iface.mac=%s\n'             "$mac"
  printf 'iface.mtu=%s\n'             "$mtu"
  printf 'iface.operstate=%s\n'       "$oper"
  printf 'iface.addr4=%s\n'           "$a4"
  printf 'iface.addr6=%s\n'           "$a6"
  printf 'wifi.associated=%s\n'       "$([ -n "$bssid" ] && echo yes || echo no)"
  printf 'wifi.ssid=%s\n'             "$ssid"
  printf 'wifi.bssid=%s\n'            "$bssid"
  printf 'wifi.freq=%s\n'             "$freq"
  printf 'route.default.dev=%s\n'     "$ddev"
  printf 'route.default.gw=%s\n'      "$dgw"
  printf 'route.default.metric=%s\n'  "$dmetric"
  printf 'route.default.src=%s\n'     "$dsrc"
  printf 'nm.general.state=%s\n'      "${nmstate-}"
  printf 'nm.device.state=%s\n'       "${nmdev-}"
  printf 'nm.device.connection=%s\n'  "${nmconn-}"
}

# --- verification ------------------------------------------------------------
verify() {
  local rc=0 addr4 gw ddev nmdev

  [ -e "/sys/class/net/$PRIMARY_IF" ] \
    || fail "primary interface '$PRIMARY_IF' does not exist on this host." \
            " (override with PRIMARY_IF=<name> if the host changed)"

  local oper; oper=$(cat "/sys/class/net/$PRIMARY_IF/operstate")
  if [ "$oper" != "up" ]; then
    printf '%s: FAIL: %s operstate is '%s', expected 'up'\n' "$SELF" "$PRIMARY_IF" "$oper" >&2
    rc=1
  else
    ok "$PRIMARY_IF operstate up"
  fi

  addr4=$(ip -4 -o addr show dev "$PRIMARY_IF" scope global 2>/dev/null | awk '{print $4}' | head -n1)
  if [ -z "$addr4" ]; then
    printf '%s: FAIL: %s has no global IPv4 address\n' "$SELF" "$PRIMARY_IF" >&2
    rc=1
  else
    ok "$PRIMARY_IF has IPv4 $addr4"
  fi

  if command -v iw >/dev/null 2>&1; then
    if iw dev "$PRIMARY_IF" link 2>/dev/null | grep -q 'Connected to'; then
      ok "$PRIMARY_IF is associated ($(iw dev "$PRIMARY_IF" link | awk -F': ' '/SSID/{print $2}'))"
    else
      printf '%s: FAIL: %s is not associated (iw link shows no AP)\n' "$SELF" "$PRIMARY_IF" >&2
      rc=1
    fi
  fi

  ddev=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -n1)
  gw=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="via") print $(i+1)}' | head -n1)
  if [ -z "$ddev" ]; then
    printf '%s: FAIL: no default route present on this host\n' "$SELF" >&2
    rc=1
  elif [ "$ddev" != "$PRIMARY_IF" ]; then
    printf '%s: FAIL: default route is via %s, not %s\n' "$SELF" "$ddev" "$PRIMARY_IF" >&2
    rc=1
  else
    ok "default route via $gw dev $ddev"
  fi

  if command -v nmcli >/dev/null 2>&1; then
    nmdev=$(nmcli -t -g GENERAL.STATE device show "$PRIMARY_IF" 2>/dev/null | head -n1 | sed 's/ (.*//')
    if [ "${nmdev:-0}" = "100" ]; then
      ok "NetworkManager reports $PRIMARY_IF connected"
    else
      printf '%s: FAIL: NetworkManager reports %s state %s (expected 100/connected)\n' \
        "$SELF" "$PRIMARY_IF" "${nmdev:-unknown}" >&2
      rc=1
    fi
  fi
  return $rc
}

# --- main --------------------------------------------------------------------
if [ "$SNAPSHOT_ONLY" -eq 1 ]; then
  snapshot || die "cannot snapshot primary interface '$PRIMARY_IF' (missing)"
  exit 0
fi

CUR="$(mktemp "${TMPDIR:-/tmp}/primary-net.XXXXXX")"
trap 'rm -f "$CUR"' EXIT
snapshot > "$CUR" || die "cannot snapshot primary interface '$PRIMARY_IF' (missing)"

if [ "$QUIET" -eq 0 ]; then
  printf -- '----- canonical snapshot (%s) -----\n' "$PRIMARY_IF"
  cat "$CUR"
  printf -- '----- checks -----\n'
fi

rc=0
verify || rc=1

if [ -n "$COMPARE_WITH" ]; then
  [ -r "$COMPARE_WITH" ] || die "--compare-with file not readable: $COMPARE_WITH"
  if diff -u "$COMPARE_WITH" "$CUR" > "${CUR}.diff" 2>&1; then
    ok "no change versus $COMPARE_WITH"
  else
    printf '%s: FAIL: primary network changed versus %s:\n' "$SELF" "$COMPARE_WITH" >&2
    cat "${CUR}.diff" >&2
    rc=1
  fi
  rm -f "${CUR}.diff"
fi

[ "$rc" -eq 0 ] && ok "primary network healthy" || printf '%s: FAIL: primary network verification failed\n' "$SELF" >&2
exit "$rc"
