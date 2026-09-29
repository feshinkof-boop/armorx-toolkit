"""Reusable byte- and field-level diff for 144-byte ArmorX configurations.

One place decides what a changed byte *is*, so the CLI never has to scatter
semantics through command code. Every entry carries an evidence string, and an
offset that no recovered field covers stays explicitly ``unknown``: this module
never invents a meaning for an undecoded byte.
"""
from __future__ import annotations

from typing import Any

from . import config as config_mod

CLASS_CRC = "crc"
CLASS_DECLARED_LENGTH = "declared_length"
CLASS_KNOWN_FIELD = "known_field"
CLASS_MAP_KEY = "map_key"
CLASS_UNKNOWN = "unknown"

KNOWN_CLASSES = (CLASS_CRC, CLASS_DECLARED_LENGTH, CLASS_KNOWN_FIELD, CLASS_MAP_KEY)

EVIDENCE = {
    CLASS_CRC: "config.crc16_gamepad() over bytes[2:144], stored big-endian at 0..1",
    CLASS_DECLARED_LENGTH: "the GamepadSet30 constructor writes 0x0090 here",
    CLASS_KNOWN_FIELD: "armorx.config field tables recovered from the old app AOT",
    CLASS_MAP_KEY: "armorx.config.MAP_KEY_CODES plus live BLE remap evidence",
    CLASS_UNKNOWN: "not decoded: no recovered field covers this offset",
}


def _index() -> dict[int, dict[str, Any]]:
    """Map every offset to its best-evidenced classification."""
    index: dict[int, dict[str, Any]] = {}
    for offset, name in ((0, "crc16"), (1, "crc16")):
        index[offset] = {"classification": CLASS_CRC, "field": name,
                         "evidence": EVIDENCE[CLASS_CRC]}
    for offset in (2, 3):
        index[offset] = {"classification": CLASS_DECLARED_LENGTH, "field": "declared_length",
                         "evidence": EVIDENCE[CLASS_DECLARED_LENGTH]}
    for name, offset in config_mod.BYTE_FIELDS.items():
        index[offset] = {"classification": CLASS_KNOWN_FIELD, "field": name,
                         "evidence": EVIDENCE[CLASS_KNOWN_FIELD]}
    for name, offset in config_mod.U32_FIELDS.items():
        for extra in range(4):
            entry = index.setdefault(offset + extra, {
                "classification": CLASS_KNOWN_FIELD, "field": name,
                "evidence": EVIDENCE[CLASS_KNOWN_FIELD],
                "note": f"byte {extra + 1} of 4 of the big-endian u32 {name}",
            })
    for name, offsets in config_mod.GROUP_FIELDS.items():
        for position, offset in enumerate(offsets):
            index.setdefault(offset, {
                "classification": CLASS_KNOWN_FIELD, "field": name,
                "evidence": EVIDENCE[CLASS_KNOWN_FIELD],
                "note": f"element {position} of the group {name}",
            })
    for source in range(32):
        offset = config_mod.MAPKEYS_START + source
        index[offset] = {"classification": CLASS_MAP_KEY, "field": f"mapKeys[{source}]",
                         "evidence": EVIDENCE[CLASS_MAP_KEY], "map_keys_source": source}
    for start, end, name in config_mod.RESERVED_RANGES:
        for offset in range(start, end + 1):
            index.setdefault(offset, {"classification": CLASS_UNKNOWN, "field": None,
                                      "region": name, "evidence": EVIDENCE[CLASS_UNKNOWN]})
    for offset in range(config_mod.CONFIG_LEN):
        index.setdefault(offset, {"classification": CLASS_UNKNOWN, "field": None,
                                  "evidence": EVIDENCE[CLASS_UNKNOWN]})
    return index


INDEX = _index()


def classify_offset(offset: int) -> dict[str, Any]:
    """Return the classification record for one offset."""
    if not 0 <= offset < config_mod.CONFIG_LEN:
        raise ValueError(f"offset {offset} is outside the 144-byte configuration")
    return dict(INDEX[offset])


def _key_names(value: int) -> str | None:
    return config_mod.CANONICAL_KEY_NAMES.get(value)


def describe_change(offset: int, before: int, after: int) -> dict[str, Any]:
    """One changed byte, fully described."""
    record = classify_offset(offset)
    entry: dict[str, Any] = {
        "offset": offset,
        "before": before,
        "after": after,
        **record,
    }
    if record["classification"] == CLASS_MAP_KEY:
        source = record.get("map_keys_source")
        entry["map_key"] = {
            "source_id": source,
            "source_name": config_mod.CANONICAL_KEY_NAMES.get(source),
            "old_target_id": before,
            "old_target_name": _key_names(before),
            "new_target_id": after,
            "new_target_name": _key_names(after),
        }
    elif record["classification"] == CLASS_KNOWN_FIELD:
        entry["before_name"] = _key_names(before)
        entry["after_name"] = _key_names(after)
    return entry


def diff_images(before: bytes, after: bytes) -> dict[str, Any]:
    """Describe every differing byte between two 144-byte images.

    Raises ValueError when either image is the wrong size: a diff over a
    different length would be meaningless.
    """
    before = bytes(before)
    after = bytes(after)
    for label, image in (("before", before), ("after", after)):
        if len(image) != config_mod.CONFIG_LEN:
            raise ValueError(f"{label} image is {len(image)} bytes, expected "
                             f"{config_mod.CONFIG_LEN}")
    changes = [describe_change(offset, before[offset], after[offset])
               for offset in range(config_mod.CONFIG_LEN)
               if before[offset] != after[offset]]
    known = [c for c in changes if c["classification"] in KNOWN_CLASSES]
    unknown = [c for c in changes if c["classification"] == CLASS_UNKNOWN]
    return {
        "changed_bytes": len(changes),
        "total_changed_bytes": len(changes),
        "changes": changes,
        "known_field_changes": known,
        "unknown_byte_changes": unknown,
        "unknown_byte_count": len(unknown),
        "has_unknown_changes": bool(unknown),
        "map_key_changes": [c["map_key"] for c in changes
                            if c["classification"] == CLASS_MAP_KEY],
        "identical": not changes,
    }


def summarise(diff: dict[str, Any]) -> str:
    """A short human-readable line for confirmation dialogs."""
    if diff.get("identical"):
        return "no changes: the target is identical to the device configuration"
    parts = [f"{diff['total_changed_bytes']} byte(s) differ"]
    for change in diff["known_field_changes"]:
        label = change.get("field") or change.get("region") or "?"
        if change["classification"] == CLASS_MAP_KEY:
            key = change["map_key"]
            parts.append(f"mapKeys[{key['source_id']}] ({key['source_name']}): "
                         f"{key['old_target_name'] or key['old_target_id']} -> "
                         f"{key['new_target_name'] or key['new_target_id']}")
        else:
            parts.append(f"{label}: {change['before']} -> {change['after']}")
    if diff["unknown_byte_count"]:
        offsets = ", ".join(str(c["offset"]) for c in diff["unknown_byte_changes"])
        parts.append(f"{diff['unknown_byte_count']} undecoded byte(s) at offsets {offsets}")
    return "; ".join(parts)
