# D4 / frame checksum verification (arithmetic, recomputed)

Every frame below was decomposed byte-by-byte and its trailing checksum recomputed as
`sum(all bytes except the last) & 0xFF` (project convention). The **recorded** value is what the
source file / document states. A corpus sweep of **227** A5/A4 frame strings across
`armorx-lab/results`, `baselines`, virtual-peripheral logs, frida traces, `armorx_research` and
`armorx-re/repo` found **exactly two** checksum deviations, both the 2.22 robustness probes
(deliberately malformed). **No accidental checksum error exists in the corpus.**

Convention note: in every recognized frame the LEN byte equals the **total frame length**
(`LEN == len(frame)`), consistent with the project's own statement in `d4-reconstruction.md` §6.
The task brief's phrasing ("LEN counts the bytes after it") does **not** match the corpus.

## Primary frames

| id | frame bytes | LEN | total | recomputed cks | recorded cks | match? | provenance |
|---|---|---:|---:|---|---|---|---|
| D4-REQ | `A5 04 D4 7D` | 4 | 4 | 0x7D | 0x7D | **MATCH** | static: 2.22/2.23/2.24/4.0.8 Blutter; live: 2.22 AVD virtual; live: 4.0.8 official HCI snoop; live: Linux harness x3 physical |
| D4-REP-VIRT-DEFAULT | `A5 06 D4 00 00 7F` | 6 | 6 | 0x7F | 0x7F | **MATCH** | live: 2.22 AVD vs virtual_armorx.py; also frozen in manifests & docs |
| D4-REP-TV-1 | `A5 06 D4 06 03 88` | 6 | 6 | 0x88 | 0x88 | **MATCH** | constructed test vector d4-reconstruction.json |
| D4-REP-TV-2 | `A5 06 D4 06 00 85` | 6 | 6 | 0x85 | 0x85 | **MATCH** | constructed test vector d4-reconstruction.json |
| D4-REP-TV-3 | `A5 06 D4 01 01 81` | 6 | 6 | 0x81 | 0x81 | **MATCH** | constructed test vector d4-reconstruction.json |
| D4-REP-BADCKSUM | `A5 06 D4 00 00 80` | 6 | 6 | 0x7F | 0x80 | **MISMATCH** | live: 2.22 AVD virtual, reply_mode=bad-checksum |
| D4-REP-TRUNCATED | `A5 04 D4 00` | 4 | 4 | — | — | — | live: 2.22 AVD virtual, reply_mode=truncated |
| D4-REP-REAL | `A5 07 D4 11 01 00 92` | 7 | 7 | 0x92 | 0x92 | **MATCH** | live: 4.0.8 official HCI snoop (logcat prints 板载mode = 1); live: Linux harness physical x3 (162448/165347/174445); frozen vector tests/vectors/real-device-vectors.json |
| 0B-REQ | `A5 04 0B B4` | 4 | 4 | 0xB4 | 0xB4 | **MATCH** | live official + physical |
| 0B-REP | `A5 05 0B 30 E5` | 5 | 5 | 0xE5 | 0xE5 | **MATCH** | live official + physical |
| EF-REQ | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | 12 | 0xA0 | 0xA0 | **MATCH** | live official + physical |
| EF-REP | `A5 0C EF BB 92 15 42 F2 1F 55 80 2A` | 12 | 12 | 0x2A | 0x2A | **MATCH** | live official + physical |
| E2-REQ | `A5 04 E2 8B` | 4 | 4 | 0x8B | 0x8B | **MATCH** | live official |
| E2-REP | `A5 10 E2 27 41 02 5A 4A 2D 58 54 00 00 00 00 7E` | 16 | 16 | 0x7E | 0x7E | **MATCH** | live official + physical |
| D6-REQ | `A5 04 D6 7F` | 4 | 4 | 0x7F | 0x7F | **MATCH** | live official + physical |
| D7-ACK | `A5 05 D7 00 81` | 5 | 5 | 0x81 | 0x81 | **MATCH** | static/documented |
| D8-COMMIT-NEW | `A4 05 D8 03 84` | 5 | 5 | 0x84 | 0x84 | **MATCH** | static corrected by Smi audit |
| D2-ENABLE | `A5 05 D2 01 7D` | 5 | 5 | 0x7D | 0x7D | **MATCH** | live official + physical |
| D2-DISABLE | `A5 05 D2 00 7C` | 5 | 5 | 0x7C | 0x7C | **MATCH** | live official + physical |
| D2-BUTTON | `A5 12 02 00 00 00 01 FD 65 00 B6 FC 4F 01 58 00 00 76` | 18 | 18 | 0x76 | 0x76 | **MATCH** | live official HCI snoop |
| D6-FRAG1 | `A4 14 D6 01 2C 40 00 90 33 FF 00 00 00 00 00 00 00 00 00 BD` | 20 | 20 | 0xBD | 0xBD | **MATCH** | live physical 162448 |
| D6-FRAG2 | `A4 14 D6 02 00 00 00 00 00 01 00 1E 1E 46 46 00 00 01 00 5A` | 20 | 20 | 0x5A | 0x5A | **MATCH** | live physical 162448 |
| D6-FRAG10 | `A4 0E D6 0A 01 0D 19 1A 1B 1C 1D 1E 1F 64` | 14 | 14 | 0x64 | 0x64 | **MATCH** | live physical 162448 |

## Deviations (both deliberate; flagged, not corrected)

| frame | recorded cks | recomputed cks | reason |
|---|---|---|---|
| `A5 06 D4 00 00 80` | `0x80` | `0x7F` | 2.22 robustness probe `--d4-reply-mode bad-checksum`; the wrong byte is the *point* (proves the app ignores the inbound D4 checksum) |
| `A5 04 D4 00` | *(none)* | *(none)* | 2.22 robustness probe `--d4-reply-mode truncated`; 4 bytes only, checksum absent by design (proves the index-4 read has no length guard) |

## Corpus-wide sweep result

- frames recognized: **227**
- checksum mismatches: **2** (both the deliberate probes above)
- no other A5/A4 frame in the corpus carries a wrong trailing byte.
