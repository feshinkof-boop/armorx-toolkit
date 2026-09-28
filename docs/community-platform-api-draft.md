# Community platform API draft (Part J, v0 draft, not implemented)

Conventions: JSON over HTTPS, `Authorization: Bearer <token>`, all timestamps RFC 3339 UTC, all ids
opaque. Errors are `{"error": {"code": "...", "message": "..."}}`. Nothing is deployed.

## Core objects

    Artifact      a configuration image, a macro, or a bundle   (immutable once published)
    Version       one revision of an artifact; has a parent     (fork = new artifact w/ parent)
    Validation    the result of running the validator on a blob
    DeviceTarget  model + firmware range an artifact is validated against

## Endpoints

### Auth
    POST /v0/auth/token            {email, password}          -> {token, expires_at}
    POST /v0/auth/refresh          -> {token}

### Artifacts
    POST /v0/artifacts
        {kind: "config"|"macro"|"bundle", name, description, tags[], device_target{model,firmware[]},
         blob_b64 | blob_sha256, fork_of?, license}
        -> {artifact_id, version_id, validation:{...}, visibility:"private"}
        Side effect: the blob is validated SYNCHRONOUSLY; a failing validation returns 422 with the
        report and nothing is stored.

    GET  /v0/artifacts/{id}                    -> metadata + latest version + validation summary
    GET  /v0/artifacts/{id}/versions           -> [{version_id, parent_id, created_at, notes}]
    GET  /v0/artifacts/{id}/versions/{v}/blob  -> the blob (content-addressed; may be a redirect)
    GET  /v0/artifacts/{id}/diff/{va}/{vb}     -> a FIELD-LEVEL diff, not a byte diff (see below)
    POST /v0/artifacts/{id}/fork               {name, notes}   -> new artifact_id (parent recorded)
    POST /v0/artifacts/{id}/publish            -> {visibility:"pending_review"}
    POST /v0/artifacts/{id}/rollback           {to_version_id} -> new version (pointer move)

### Discovery
    GET /v0/search?q=&tag=&model=&firmware=&kind=&sort=validated_use|new|likes
    GET /v0/tags                               -> [{tag, count}]
    POST /v0/artifacts/{id}/like | /unlike
    POST /v0/artifacts/{id}/favorite | /unfavorite
    GET  /v0/artifacts/{id}/stats              -> {downloads, validated_applies, likes, favorites}

### Safety
    POST /v0/artifacts/{id}/report             {reason, detail}
    GET  /v0/moderation/queue                  (moderator scope)

### Compatibility
    GET /v0/compat/{model}/{firmware}          -> {supported_kinds[], known_byte_map_version}

## The diff contract (this is the important one)

`GET /diff` never returns raw bytes. It returns the **semantic** difference using the per-byte evidence
map, so a reader sees what actually changes and what is unknown:

    {
      "fields": [
        {"name":"dpi_stick_left", "a":1200, "b":1600, "grade":"STRONG EVIDENCE"},
        {"name":"bytes[131..134]", "a":"00 00 00 00", "b":"01 00 00 00", "grade":"UNKNOWN"}
      ],
      "checksum": {"a_valid": true, "b_valid": true},
      "unknown_regions_changed": 1
    }

`unknown_regions_changed` is surfaced deliberately: a config that differs in bytes we do not understand
is exactly the case a user must be told about before applying it.

## Validation report shape

    {
      "ok": true,
      "checks": [
        {"id":"size_144", "ok": true},
        {"id":"checksum", "ok": true, "computed":"0x73", "declared":"0x73"},
        {"id":"device_target", "ok": true, "model":"ZJ-XT", "firmware":["2741"]},
        {"id":"unknown_regions", "ok": true, "count": 0, "policy":"warn"},
        {"id":"undocumented_opcodes", "ok": true, "count": 0}
      ],
      "warnings": []
    }

## Status codes worth pinning down

| code | meaning |
|---|---|
| 422 | validation failed (report included; nothing stored) |
| 409 | identical blob already published - return the existing artifact instead of duplicating |
| 412 | device target mismatch (model/firmware) - block at apply, warn at download |
| 451 | content removed by moderation (kept as a tombstone so citations do not dangle) |
