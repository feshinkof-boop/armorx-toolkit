# Community platform schema (Part J, draft)

Relational sketch. Postgres-flavoured types; the choices that matter are commented.

    -- users -------------------------------------------------------------------
    users(
      id            uuid pk,
      handle        citext unique not null,
      email         citext unique not null,
      created_at    timestamptz not null default now(),
      trust_level   smallint not null default 0,   -- gates publishing; see moderation
      is_vendor     boolean not null default false -- only the vendor may mark "official"
    )

    -- artifacts: the stable identity of a shareable thing ---------------------
    artifacts(
      id            uuid pk,
      kind          text not null check (kind in ('config','macro','bundle')),
      name          text not null,
      owner_id      uuid not null references users(id),
      forked_from   uuid null references artifacts(id),   -- remix lineage
      created_at    timestamptz not null default now(),
      visibility    text not null default 'private'
                    check (visibility in ('private','pending_review','public','removed')),
      official      boolean not null default false,       -- vendor-marked only
      license       text not null default 'CC-BY-4.0',
      deleted_at    timestamptz null                      -- tombstone, never hard-delete
    )

    -- versions: immutable revisions; rollback is a pointer, not a rewrite ------
    artifact_versions(
      id            uuid pk,
      artifact_id   uuid not null references artifacts(id),
      parent_id     uuid null references artifact_versions(id),
      blob_sha256   char(64) not null,
      blob_bytes    integer not null,        -- configs: exactly 144; macros: schema-bounded
      notes         text,
      created_by    uuid not null references users(id),
      created_at    timestamptz not null default now(),
      is_current    boolean not null default false,   -- exactly one true per artifact (partial unique)
      unique (artifact_id, blob_sha256)
    )

    -- blobs: content-addressed, deduped, never overwritten --------------------
    blobs(
      sha256        char(64) pk,
      bytes         integer not null,
      storage_key   text not null,
      first_seen_at timestamptz not null default now()
    )

    -- validation: one row per (version, validator version) -------------------
    validations(
      id             uuid pk,
      version_id     uuid not null references artifact_versions(id),
      validator_rev  text not null,          -- re-validate when the rules change
      ok             boolean not null,
      report         jsonb not null,
      checked_at     timestamptz not null default now(),
      unique (version_id, validator_rev)
    )

    -- device compatibility ---------------------------------------------------
    devices(
      model          text not null,          -- 'ZJ-XT'
      firmware       text not null,          -- '2741'
      byte_map_rev   text not null,          -- which evidence map was current
      primary key (model, firmware)
    )
    artifact_targets(
      artifact_id    uuid not null references artifacts(id),
      model          text not null,
      firmware_min   text null,
      firmware_max   text null,
      primary key (artifact_id, model)
    )

    -- taxonomy + engagement --------------------------------------------------
    tags(id serial pk, slug citext unique not null, label text not null)
    artifact_tags(artifact_id uuid references artifacts(id), tag_id int references tags(id),
                  primary key (artifact_id, tag_id))
    likes(user_id uuid references users(id), artifact_id uuid references artifacts(id),
          created_at timestamptz not null default now(), primary key (user_id, artifact_id))
    favorites(... same shape ...)
    downloads(id bigserial pk, artifact_id uuid, version_id uuid, user_id uuid null,
              at timestamptz not null default now(), client text)
      -- downloads are appended, never updated: counts are derived, so they cannot be inflated by
      -- a later row edit.

    -- moderation -------------------------------------------------------------
    reports(id bigserial pk, artifact_id uuid, version_id uuid null, reporter_id uuid,
            reason text not null, detail text, at timestamptz not null default now(),
            state text not null default 'open' check (state in ('open','actioned','rejected')))
    audit_log(id bigserial pk, actor_id uuid, action text not null, subject text not null,
              detail jsonb, at timestamptz not null default now())
      -- every moderation action and every rollback writes here.

## Indexes that carry their weight

- `artifact_versions (artifact_id, is_current) where is_current` - fetch the head cheaply.
- `artifact_versions (blob_sha256)` - "who else ships this exact config" (409 dedupe).
- `validations (version_id, validator_rev)` - avoid re-running the validator.
- full-text index on `artifacts (name, description)` plus `artifact_tags (tag_id)` - search without
  keyword stuffing winning.
- `downloads (artifact_id, at)` - counters over windows rather than a mutable integer.

## Design notes that prevent whole classes of problems

- **No mutable counters.** Likes/favorites/downloads are rows; totals are derived. Nothing to
  desynchronise, nothing to farm by editing a row.
- **No hard deletes.** Removed content becomes a tombstone so links and citations from the research
  notes stay valid, and moderation history survives.
- **Validation is versioned by validator revision.** When the rules change (a new byte's meaning is
  proven), old artifacts are re-validated rather than silently trusted.
- **Firmware compatibility is a table, not a string.** A config validated on `2741` is stored as such;
  the client refuses to apply it to an unlisted firmware and says why.
- **Private by default.** Publishing is an explicit transition through `pending_review`.
