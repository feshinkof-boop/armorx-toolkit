#!/usr/bin/env python3
"""Read-oriented BIGBIG WON / ARMORX Pro community/config exchange client.

This tool reproduces known client-compatible request shapes for interoperability
and preservation. It does not brute-force share codes, enumerate identifiers,
or perform destructive operations.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://m.bigbigwon.com:8080"


def build_list_payload(phone_uuid: str, dev_uuid: str, *, page_num: int = 1, config_type: int = 1) -> dict[str, Any]:
    if page_num < 1:
        raise ValueError("page_num must be >= 1")
    return {
        "phoneUuid": phone_uuid,
        "devUuid": dev_uuid,
        "pageNum": page_num,
        "configType": config_type,
    }


def build_import_payload(share_code: str, *, phone_uuid: str | None = None, dev_uuid: str | None = None) -> dict[str, Any]:
    code = share_code.strip()
    if not code:
        raise ValueError("share code cannot be empty")
    if (phone_uuid is None) ^ (dev_uuid is None):
        raise ValueError("phone_uuid and dev_uuid must be supplied together")
    payload: dict[str, Any] = {"shareCode": code}
    if phone_uuid is not None and dev_uuid is not None:
        payload["phoneUuid"] = phone_uuid
        payload["devUuid"] = dev_uuid
    return payload


def post_json(base_url: str, path: str, payload: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"server returned non-JSON data: {raw[:300]!r}") from exc


def write_result(obj: Any, output: str | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_list(args: argparse.Namespace) -> int:
    payload = build_list_payload(
        args.phone_uuid,
        args.dev_uuid,
        page_num=args.page_num,
        config_type=args.config_type,
    )
    if args.dry_run:
        write_result(payload, args.output)
        return 0
    result = post_json(args.base_url, "/dev/queryConfigList", payload, timeout=args.timeout)
    write_result(result, args.output)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    payload = build_import_payload(
        args.share_code,
        phone_uuid=args.phone_uuid,
        dev_uuid=args.dev_uuid,
    )
    if args.dry_run:
        write_result(payload, args.output)
        return 0
    result = post_json(args.base_url, "/dev/importShareConfig", payload, timeout=args.timeout)
    write_result(result, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Read-oriented ARMORX Pro community/config exchange client"
    )
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--timeout", type=float, default=10.0)

    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("list", help="query configurations using the reproduced client request shape")
    q.add_argument("--phone-uuid", required=True)
    q.add_argument("--dev-uuid", required=True)
    q.add_argument("--page-num", type=int, default=1)
    q.add_argument("--config-type", type=int, default=1)
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("-o", "--output")
    q.set_defaults(func=cmd_list)

    q = sub.add_parser("import-code", help="import one known share code")
    q.add_argument("share_code")
    q.add_argument("--phone-uuid")
    q.add_argument("--dev-uuid")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("-o", "--output")
    q.set_defaults(func=cmd_import)

    return p


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
