#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

VERSION=$(PYTHONPATH=src python -c 'import armorx; print(armorx.__version__)')
DIST="$ROOT/dist"
STAGE_ROOT="$DIST/linux-package"
STAGE="$STAGE_ROOT/ArmorX-Toolkit-Linux-v$VERSION"

rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE"

python -m build

WHEEL="$DIST/armorx_toolkit-${VERSION}-py3-none-any.whl"
SDIST="$DIST/armorx_toolkit-${VERSION}.tar.gz"

test -f "$WHEEL"
test -f "$SDIST"

cp "$WHEEL" "$STAGE/"
cp "$ROOT/packaging/linux/install.sh" "$STAGE/"
cp "$ROOT/packaging/linux/uninstall.sh" "$STAGE/"
cp "$ROOT/packaging/linux/README.txt" "$STAGE/"
cp "$ROOT/LICENSE" "$STAGE/"
chmod 755 "$STAGE/install.sh" "$STAGE/uninstall.sh"

ARCHIVE="$DIST/ArmorX-Toolkit-Linux-v${VERSION}.tar.gz"
tar -C "$STAGE_ROOT" -czf "$ARCHIVE" "ArmorX-Toolkit-Linux-v$VERSION"

MANIFEST="$DIST/ArmorX-Toolkit-Linux-v${VERSION}-SHA256SUMS.txt"
(
  cd "$DIST"
  sha256sum     "armorx_toolkit-${VERSION}-py3-none-any.whl"     "armorx_toolkit-${VERSION}.tar.gz"     "ArmorX-Toolkit-Linux-v${VERSION}.tar.gz"
) > "$MANIFEST"

printf '%s\n' "$ARCHIVE" "$MANIFEST"
