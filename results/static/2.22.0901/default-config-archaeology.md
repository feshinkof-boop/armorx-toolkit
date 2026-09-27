# Embedded default-config archaeology — BIGBIG WON 2.22.0901

Frozen APK: sha256 `785684ec…c0361c`. Read-only over the untouched APK, the extracted tree
`apk/extracted/2.22.0901/`, and the existing Blutter tree at
`static/blutter/2.22.0901/blutter_out/`. Producer: `config_arch.py` (this pass).

## Method

Default config images are stored in the Dart AOT string pool as **decimal byte arrays**
(`"String: \"[0,0,0,88,…]\""`). Extraction command:

```bash
grep -a -oE '\[pp\+0x[0-9a-f]+\] String: "\[([0-9]+(, ?[0-9]+)+)\]"' pp.txt
```

Each array is parsed to bytes. Header rule (identical to the later builds, and self-consistent with
the length prefix): **bytes 0–1 = CRC-16/MODBUS big-endian, bytes 2–3 = total length big-endian**.
CRC is recomputed with `CRC-16/MODBUS` (init `0xFFFF`, poly `0xA001`) **over bytes 2..end**.

## 1. Assets that could be config blobs

`assets/flutter_assets/**` (15 entries) contains **only** images/fonts/JSON:
`dev_armorx.png`, `dev_rainbow.png`, `left_stick.png`, `right_stick.png`, `splash_logo.png`,
`y_axis.gif`, `z_axis.gif`, `fonts/MjIcons.ttf`, `MaterialIcons-Regular.otf`,
`packages/**/CupertinoIcons.ttf`, `toastify.css/js`, `AssetManifest.json`, `FontManifest.json`,
`NOTICES.Z`. **No default-config or protocol blob exists under `assets/`** (PROVEN STATIC —
`find assets -type f`; all files are the listed media/JSON). No config images hide in `res/`,
`classes.dex`, `resources.arsc` or the protos either.

## 2. Config-like arrays in the 2.22 Dart pool — exactly two

| # | pp offset | len | declared len | sha256 | stored CRC | recomputed CRC-16/MODBUS (bytes 2..end) | self-valid | family |
|--:|---|---:|---:|---|---|---|---|---|
| 1 | `pp+0x46480` | 88 | 0x0058 | `9eaea1d6a42c49a45ccd2bc5e6c4e44345e2558f7dd989c06a90e9cae4a9afa6` | `0x0000` | `0xC800` | no | universal 88-byte default |
| 2 | `pp+0x46488` | 144 | 0x0090 | `b8f5735ccb070b36b93651e1d058b54a23247ba7edb38872be3cd7697e45e595` | `0x0000` | `0xB811` | no | ARMOR-X Pro 144 family |

Both stored CRCs are `0x0000` — these are **template/placeholder defaults** (the app writes the real
CRC before transmitting), exactly as in 2.23/2.24/4.0.8 where the "defaults" also carry `0x0000`.
Only the 240/335/456/484/508-family images in later builds are self-validating.

Raw bytes:

```
88-byte : [0,0,0,88, 0,0,0,0,0,60,60,44,10,0,0,0, 0,0,0,0,0,0,0,0,0,0,80,42,80,42,12,12,
           90,10,90,10,30,30,70,70,30,30,70,70, 0,0,0,0,0,0,0,0,0,0,0,4, 0..31]
144-byte: [0,0,0,144, 0,255,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,1,0,30,30,70,70,0,0,1,0,30,30,70,70,
           0,0,2,0,2,2,0,0,0,0,0,10,60,60,42,0, 0,0,0,10,60,60,42,0,0,0,0,10,60,60,42, 0…,0..31]
```

**Device mapping (STRONG EVIDENCE):** the 88-byte image is the same blob used by every later build
for the Rainbow/GamepadSet (0x58) family. The 144-byte image is the **ARMOR-X Pro** 144-byte
`GamepadSet30` image — see the byte-for-byte result below — which matches the only ArmorX member of
the 4-member device enum (`devArmorX`, index 3). **No 240/280/335/456/484/508 image exists in 2.22**,
so 2.22 supports only the 88-byte and 144-byte config families.

## 3. Byte-for-byte comparison with the later builds

Command: extract the same arrays from each build's Blutter pool and diff element-wise.

| build | pp.txt | 88-byte | 144-byte (Rainbow-family `1fa5afe2`) | 144-byte (ArmorX `bc536085`) | other families |
|---|---|---|---|---|---|
| **2.22.0901** | `…/armorx-lab/static/blutter/2.22.0901/blutter_out/pp.txt` | `9eaea1d6…afa6` | **absent** | **present (1 byte differs)** | none |
| 2.23 | `~/armorx/re/blutter_out/pp.txt` | `9eaea1d6…afa6` | `1fa5afe2401d17c2…` | `bc536085f138a2ed…` | 240 |
| 2.24 | `~/armorx/re/v224/blutter_out/pp.txt` | `9eaea1d6…afa6` | `1fa5afe2401d17c2…` | `bc536085f138a2ed…` | 240×3, 280, 484 |
| 4.0.8 | `~/armorx-re/mygt408/blutter_out/pp.txt` | `9eaea1d6…afa6` | `1fa5afe2401d17c2…` | `bc536085f138a2ed…` | 240×3, 280×2, 335, 456, 484, 508 |

### 88-byte image — byte-for-byte identical to every later build

`2.22`, `2.23`, `2.24`, `4.0.8` all hold the **same** 88-byte default: 0 differing bytes
(`sha256 9eaea1d6a42c49a4…`). This is device-wide and version-invariant. **PROVEN STATIC.**

### 144-byte image — the ARMOR-X lineage, differing by exactly one byte

2.22's 144-byte image differs from the image 2.23/2.24/4.0.8 store as `bc536085f138a2ed…` at exactly
**one** byte:

| byte offset | 2.22.0901 | 2.23 / 2.24 / 4.0.8 |
|---|---|---|
| 4 | `0x00` | `0x33` (51) |

All other 143 bytes are identical. Per the toolkit field map (baseline `config-144-reconstruction.md`)
offset 4 is the first serialised parameter (`GamepadParam30` index 0 — `motorSpeedIdx`, name
unproven); in 2.22 the ARMOR-X Pro default leaves it `0`, from 2.23 on it is `0x33`. The 2.22 image
also differs from the *other* later 144-byte image (`1fa5afe2…`) at 8 bytes
(`[4,10,11,12,13,16,18,36]`) — but that `1fa5afe2…` image is **not present in 2.22 at all**.

```bash
# 2.22 144-byte vs bc536085 (ArmorX):  1 differing byte @ [4]
# 2.22 144-byte vs 1fa5afe2:           8 differing bytes @ [4,10,11,12,13,16,18,36]
```

### Conflict with the imported baseline (flagged, not papered over)

`baselines/imported-research/config-144-reconstruction.md` quotes the 4.0.8 ARMOR-X Pro 144 default
as `[0,0,0,144,51,255,0,0,0,0,10,5,10,5,…]` (define.dart:512). Those bytes match the image the
**2.23 manifest labels "Rainbow-family" (`1fa5afe2…`, with `10,5,10,5` at offsets 10–13)**, not the
image the 2.23 manifest labels "ARMOR-X Pro" (`bc536085…`, which has zeros at 10–13). The two prior
sources therefore disagree on which 144-byte image belongs to ARMOR-X Pro.

* **PROVEN STATIC (this pass):** 2.22 ships exactly one 144-byte image, equal to `bc536085…` up to
  byte 4; it does **not** ship `1fa5afe2…`.
* **CONTRADICTED / UNRESOLVED:** which 144 image is ARMOR-X Pro's. 2.22's device enum has a single
  ArmorX member and a single 144 image, so *within 2.22* the only 144 default must serve ArmorX —
  but the byte values (`0,0` at 10–13) match the image later labelled the non-ArmorX one.
  Resolving which device each 144 image binds to requires the `toList`/`curDevice` asm dispatch,
  which is out of scope for this inventory pass and is left as a named follow-up.

## 4. Summary

* Embedded default-config images in 2.22: **two** (88-byte and 144-byte). No others anywhere in the
  APK.
* 88-byte default is **byte-identical to all later builds**.
* 144-byte default is the ARMOR-X lineage, differing from all later builds by **exactly byte 4**
  (`0x00` vs `0x33`).
* 2.22 predates the 240/280/335/456/484/508 config families entirely.
* Assets contain no config blobs.