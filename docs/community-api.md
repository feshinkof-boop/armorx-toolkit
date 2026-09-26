# Community/config exchange research

This document tracks the currently reproduced **BIGBIG WON / ARMORX Pro** community/config exchange behavior.

The goal is interoperability and preservation, not service enumeration.

## Config list

A reproduced config-list request uses:

```http
POST /dev/queryConfigList
Content-Type: application/json
```

with a body shaped like:

```json
{
  "phoneUuid": "<phone-id>",
  "devUuid": "<controller-id>",
  "pageNum": 1,
  "configType": 1
}
```

The response contains pagination metadata and a `configList` array.

Important: `configType = 1` is proven as the value used by this client path. It should **not** be treated as a universal public/private visibility flag.

## Share-code import

The service also exposes a share-code import flow using:

```http
POST /dev/importShareConfig
```

A minimal accepted request has been observed with:

```json
{
  "shareCode": "<code>"
}
```

Some client flows may include device identifiers as additional fields.

## Scope warning

A config-list result is scoped to the supplied identifiers and request parameters. A small result set does not prove the global service contains no other configurations.

## Safety

The repository does not include brute-force code, credential testing, destructive operations, or broad identifier enumeration.

Community tooling should stay limited to normal client-compatible behavior and data the user is authorized to access.


## Cross-client reconciliation (2026-09-25)

The Windows Assistant 1.0.6.1 (WndMgr.dll `CJsonCreator`) uses the same host
(`http://m.bigbigwon.com:8080`) and the same `/dev/*` endpoint family with the
same JSON field names. Full three-client endpoint matrix (Android 2.23,
Android 2.24 adds `/dev/queryGameList`, Windows adds `/dev/queryFirewareList`):
see `research/server-api-map.md`. No brute-force or enumeration behavior is
used or documented.
