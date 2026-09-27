#!/usr/bin/env python3
"""Build the four-way version matrix (2.22.0901 / 2.23.0609 / 2.24.0919 / 4.0.8) from the per-build
manifests in /home/salamanka/armorx-lab/apk/manifests/.

Usage:
  /usr/bin/python3 /home/salamanka/armorx-lab/scripts/compare_versions.py \
      [--manifests DIR] [--out-md PATH] [--out-json PATH]

Design notes:
  * It never invents a field. A field missing from a manifest (or explicitly "UNKNOWN") is printed
    as UNKNOWN in the table, because "not analysed yet" and "not present in the binary" are
    different findings and must not be conflated.
  * Field lookup is tolerant: manifests written by different passes use different key paths
    (e.g. ble.library vs transport.ble_library), so each row declares a list of candidate paths.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

LAB = "/home/salamanka/armorx-lab"
VERSIONS = ["2.22.0901", "2.23.0609", "2.24.0919", "4.0.8"]
# version label -> manifest filename (earlier passes named the manifests after the short version)
MANIFEST_FILE = {"2.22.0901": "2.22.0901.json", "2.23.0609": "2.23.json",
                 "2.24.0919": "2.24.json", "4.0.8": "4.0.8.json"}

# row label -> candidate key paths (dotted). First hit wins.
ROWS: list[tuple[str, list[str]]] = [
    ("original filename", ["original_filename", "file.original_filename"]),
    ("sha256", ["sha256", "hashes.sha256"]),
    ("sha1", ["sha1", "hashes.sha1"]),
    ("size", ["size", "size_bytes", "file.size"]),
    ("package", ["package", "package_name", "identity.package"]),
    ("versionName", ["versionName", "version_name", "identity.versionName"]),
    ("versionCode", ["versionCode", "version_code", "identity.versionCode"]),
    ("signer", ["signer", "signing_certificate", "signature.certificate"]),
    ("minSdk", ["minSdk", "min_sdk", "sdk.minSdk"]),
    ("targetSdk", ["targetSdk", "target_sdk", "sdk.targetSdk"]),
    ("ABIs", ["abis", "abi_set", "abi"]),
    ("split structure", ["split_structure", "splits", "layout"]),
    ("Dart version", ["dart_version", "dart", "runtime.dart"]),
    ("Flutter version", ["flutter_version", "runtime.flutter"]),
    ("BLE library", ["ble_library", "ble.library", "transport.ble_library"]),
    ("device enum", ["device_enum", "device_enum_size", "device_enum.count"]),
    ("ARMOR-X enum id", ["armorx_enum_value", "armorx_enum_id", "device_enum.armorx_id"]),
    ("config families", ["config_sizes", "config_families"]),
    ("ARMOR-X config length", ["armorx_config_length", "armorx.conf_length", "config_length_rule"]),
    ("config CRC", ["config_crc", "crc.algorithm"]),
    ("E2 readFirmware", ["@E2"]),
    ("0x0B / 0x0E", ["@0B", "@0E"]),
    ("D6 / D7", ["@D6", "@D7"]),
    ("D4 / D2", ["@D4", "@D2"]),
    ("0x70 lighting", ["@70"]),
    ("D8 macro", ["@D8"]),
    ("FC / F6 DPI", ["@FC", "@F6"]),
    ("AB motion DPI", ["@AB"]),
    ("lighting", ["lighting", "lighting.summary"]),
    ("turbo", ["turbo", "turbo.summary"]),
    ("server host", ["server_hosts", "server_host", "server.host"]),
    ("endpoints", ["server_endpoints", "endpoints", "server.endpoints"]),
    ("key-ID table", ["key_id_table", "key_ids"]),
    ("BLE UUID table", ["ble_uuid_table", "scan_prefixes", "ble.scan_prefixes"]),
]


OPCODE_ALIASES = {
    "@E2": ["E2", "e2", "0xE2", "0xe2"],
    "@0B": ["0B", "0b", "0x0B", "0x0b"],
    "@0E": ["0E", "0e", "0x0E", "0x0e"],
    "@D6": ["D6", "d6", "0xD6", "0xd6"],
    "@D7": ["D7", "d7", "0xD7", "0xd7"],
    "@D4": ["D4", "d4", "0xD4", "0xd4"],
    "@D2": ["D2", "d2", "0xD2", "0xd2"],
    "@70": ["70", "0x70"],
    "@D8": ["D8", "d8", "0xD8", "0xd8"],
    "@FC": ["FC", "fc", "0xFC", "0xfc", "F6", "0xF6"],
    "@F6": ["F6", "f6", "0xF6", "0xf6"],
    "@AB": ["AB", "0xAB"],
}


def _opcode_lookup(doc: dict, token: str):
    """Find an opcode entry in whichever opcode structure the manifest uses (tolerant)."""
    names = OPCODE_ALIASES[token]
    containers = []
    for key in ("opcode_inventory", "opcodes", "commands"):
        node = doc.get(key)
        if node is not None:
            containers.append(node)
    for node in containers:
        if isinstance(node, dict):
            for n in names:
                if n in node:
                    return node[n]
            # nested dicts of dicts (e.g. {"A5": {"0B": {...}}})
            for sub in node.values():
                if isinstance(sub, dict):
                    for n in names:
                        if n in sub:
                            return sub[n]
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    op = str(item.get("opcode") or item.get("op") or item.get("code") or "").upper()
                    if op.replace("0X", "") in [n.upper().replace("0X", "") for n in names]:
                        return {k: item[k] for k in item if k in
                                ("opcode", "name", "status", "role", "frame", "builder", "address", "evidence")}
    return None


def get(doc: dict, paths: list[str]):
    for p in paths:
        cur = doc
        ok = True
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, "", [], {}):
            return cur
    return None


def fmt(v) -> str:
    if v is None:
        return "UNKNOWN"
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
        return s if len(s) <= 120 else s[:117] + "..."
    return str(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifests", default=os.path.join(LAB, "apk/manifests"))
    ap.add_argument("--out-md", default=os.path.join(LAB, "results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.md"))
    ap.add_argument("--out-json", default=os.path.join(LAB, "results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.json"))
    args = ap.parse_args()

    docs: dict[str, dict] = {}
    for v in VERSIONS:
        p = os.path.join(args.manifests, MANIFEST_FILE.get(v, f"{v}.json"))
        if os.path.isfile(p):
            try:
                with open(p) as fh:
                    docs[v] = json.load(fh)
            except Exception as exc:  # noqa: BLE001
                docs[v] = {"_error": f"unparsable manifest: {exc}"}
        else:
            docs[v] = {"_missing": True}

    table: dict[str, dict[str, str]] = {}
    lines = [
        "# Four-way version matrix: 2.22.0901 / 2.23.0609 / 2.24.0919 / 4.0.8",
        "",
        "Generated by `scripts/compare_versions.py` from `apk/manifests/*.json`.",
        "`UNKNOWN` means the manifest does not carry the field (not analysed, or not present) — it never",
        "means 'same as another column'. Per-field evidence labels live in the individual manifests and in",
        "`results/version-diff/static-version-matrix.md`.",
        "",
        "| field | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |",
        "|---|---|---|---|---|",
    ]
    for label, paths in ROWS:
        row = {}
        for v in VERSIONS:
            doc = docs[v]
            if doc.get("_missing"):
                row[v] = "MISSING_ARTIFACT"
            elif doc.get("_error"):
                row[v] = f"ERROR: {doc['_error']}"
            elif paths and paths[0].startswith("@"):
                row[v] = fmt(_opcode_lookup(doc, paths[0]))
            else:
                val = get(doc, paths)
                if isinstance(val, list) and val and isinstance(val[0], dict) and "name" in val[0]:
                    # enum table -> show size plus the member list
                    names = ", ".join(f"{m.get('id')}={m.get('name')}" for m in val)
                    val = f"{len(val)} members: {names}"
                row[v] = fmt(val)
        table[label] = row
        lines.append("| " + " | ".join([label] + [row[v] for v in VERSIONS]) + " |")

    lines += [
        "",
        "## Multi-value fields (full, not truncated)",
        "",
    ]
    for label, paths in ROWS:
        if any(len(table[label][v]) > 118 for v in VERSIONS):
            lines.append(f"### {label}")
            lines.append("")
            for v in VERSIONS:
                lines.append(f"* **{v}**: {table[label][v]}")
            lines.append("")

    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)
    with open(args.out_md, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(args.out_json, "w") as fh:
        json.dump(
            {
                "generated_by": "scripts/compare_versions.py",
                "versions": VERSIONS,
                "manifests": {v: os.path.join(args.manifests, MANIFEST_FILE.get(v, f"{v}.json")) for v in VERSIONS},
                "manifest_present": {v: not docs[v].get("_missing") for v in VERSIONS},
                "rows": table,
            },
            fh,
            indent=1,
        )
    missing = [v for v in VERSIONS if docs[v].get("_missing")]
    print(f"wrote {args.out_md} and {args.out_json}")
    if missing:
        print("MISSING_ARTIFACT manifests: " + ", ".join(missing), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
