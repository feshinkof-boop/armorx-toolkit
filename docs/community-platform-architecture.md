# Community platform architecture (Part J, design only - not deployed)

Scope: a place where ARMOR-X Pro owners share **configurations** (the 144-byte image plus its
interpretation), **macros**, and **profile bundles**, with fork/remix, validation, moderation, and
version/firmware compatibility. Nothing here was deployed, and no code was written against a live host.

## Why this is feasible at all (the platform rests on three proven facts)

1. The configuration is a **144-byte image with an 8-bit trailing checksum** we can verify offline
   (`config_verify` in `armorx_lab.frames`), so shared content is **mechanically validatable**.
2. The image has a **known, per-byte evidence map** (`config-byte-evidence-map.json`), so a shared
   config can be presented as *named fields* with an honest "unknown" for the rest.
3. **D2/Button-Test, DPI, motion and lighting all have static app-side encoders**, so a shared artifact
   can be described in terms of intent ("remap A→LB, DPI preset 3") rather than raw bytes - and a
   reviewer can compare intents, not just hashes.

## Shape of the system

    client (CLI / GUI) ──HTTP──▶ API ──▶ validation service ──▶ object storage (config blobs)
                                   │                                │
                                   └──▶ database (metadata, users, versions) ──▶ moderation queue

Three principles:

- **Blobs and metadata are separate.** The configuration image is content-addressed (`sha256`); the
  database holds only metadata and a pointer. Two identical uploads are one object.
- **Validation is a gate, not a suggestion.** Nothing becomes publicly listable until it passes the
  checksum/format/compatibility checks (see `-schema.md`).
- **Everything is versioned and forkable.** A config never changes in place; an edit produces a new
  version with a parent pointer, which is what makes remix and rollback trivial.

## Components

| component | responsibility | notes / honest limits |
|---|---|---|
| **API** | auth, upload, search, list, fork, download, report | stateless, rate-limited; no direct DB access from clients |
| **validator** | format + checksum + compatibility + *safety* checks | reused by both upload and CI of the client repo; the same code path that validates a local file |
| **moderation queue** | human review of flagged content + spot checks | automated filters only *flag*; they never publish |
| **storage** | content-addressed blobs | dedupe by hash; no overwrite semantics |
| **database** | metadata, users, versions, tags, counters | see the schema document |
| **client** | import/export, preview/diff, apply | applying a config to a device is a **local** action with its own confirm step |

## Threat model (what we protect against)

| threat | mitigation |
|---|---|
| **Malformed config bricking a pad** | format+checksum gate; unknown-byte policy; apply is local and reversible (baseline readback first) |
| **Malicious macro / hidden payload** | macros are decoded into steps, shown to the reviewer, and rejected if they encode undocumented opcodes; no raw-blob apply |
| **Exfiltration via "configs"** | blobs are **exactly** 144 bytes for configs and schema-constrained for macros; no arbitrary-length files |
| **Spam / SEO abuse** | publishing requires an account older than N days plus at least one validated upload; search ranks by validated-use, not by keyword |
| **Impersonation of a vendor config** | only the vendor account can mark content "official"; everyone else is "community", visibly |
| **Silent drift when firmware changes** | every artifact carries the firmware/model it was validated against; mismatches are shown at download and blocked at apply |
| **Rollback abuse** | rollback is metadata-only (pointer move); the previous version is never deleted |

## Non-goals (stated so they are not smuggled in later)

- No firmware distribution and no OTA. The platform ships **configuration and macros**, never code that
  runs on the pad's MCU.
- No account-to-device binding on the server: the server never talks to a pad.
- No "auto-apply": downloading never writes to a device.
