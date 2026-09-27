#!/bin/bash
# Emergency restore wrapper - see README.md next to this script.
# It refuses to write unless the baseline manifest has restore_verified: true.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 "$HERE/emergency-restore.py" "$@"
