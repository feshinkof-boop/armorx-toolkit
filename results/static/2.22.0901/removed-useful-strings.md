# Strings present in 2.22.0901 but ABSENT from 2.23 / 2.24 / 4.0.8 — useful subset

Frozen APK: sha256 `785684ec…c0361c`. Read-only. Producer: `removed_useful.py` (this pass).

## Method

Dart-pool-to-Dart-pool diff (apples to apples), not raw `strings` diffs:

```bash
# 1. pool literal set per build
grep -o 'String: ".*"' <build>/blutter_out/pp.txt      # 2.22 lab tree; 2.23 ~/armorx/re; 2.24 ~/armorx/re/v224; 4.0.8 ~/armorx-re/mygt408
# 2. 2.22-only  =  pool(2.22) \ ( pool(2.23) ∪ pool(2.24) ∪ pool(4.0.8) )
```

Pool sizes: 2.22 = 15,023 · 2.23 = 16,194 · 2.24 = 17,365 · 4.0.8 = 18,593.
**2.22-only pool strings: 310.** (2.22 is the oldest build, so its vocabulary is largely a subset
of the later ones — hence a small unique set.)

## Verdict (the important part)

> **No protocol-meaning or field-meaning string is unique to 2.22.0901.** The 310-string 2.22-only
> set is ~99% Flutter-framework internals plus a handful of device-label / URL strings. Therefore
> **no currently-UNKNOWN protocol field can be named from a 2.22-only string** — this pass finds no
> such hint. This is reported as a negative result, not padded with framework noise.

## App-meaningful 2.22-only strings (the entire useful residue)

| string | category | why it matters | later builds |
|---|---|---|---|
| `"RAINBOW"` | device label | uppercase Rainbow label; 2.22 carries both `"Rainbow"` and `"RAINBOW"` | absent (0 hits) |
| `"ArmorX Pro"` | device label | mixed-case ArmorX label; 2.22 carries both `"ArmorX Pro"` and `"ARMOR-X Pro"` | absent (0 hits) |
| `oss…/product-pic/AEMOR-X/…/armorx Pro user manual-EN.pdf` | URL | EN/JP ArmorX-Pro manual URLs | dropped (later builds keep only 1 AEMOR-X URL) |
| `oss…/product-pic/AEMOR-X/…/armorx Pro 电子说明书-CN.pdf` / `…-JP.pdf` | URL | CN/JP manual URLs (2.22 has 3 AEMOR-X URLs vs 1 later) | partially dropped |

None of these names a protocol field; they are naming/URL variants.
Confirmed by direct grep: `grep -c '"RAINBOW"' / 'ArmorX Pro" / 'AEMOR-X'` → 2.22 `1 / 1 / 3`,
2.23/2.24/4.0.8 `0 / 0 / 1`.

## What the other ~306 strings are (framework noise — not app meaning)

Library-version artifacts only, e.g.:

* `webview_flutter_android` pigeon channels — `dev.flutter.pigeon.WebViewHostApi.*`,
  `WebSettings(...)`, `…JavascriptMode`, `updateSettings`.
* `provider` package diagnostics — the long `ProviderNotFoundError` help text block.
* Dart/Flutter engine internals — `Expected CDATA content`, `No channel registered with name`,
  `Only square matrix dimensions are supported`, GLSL shader fragments
  (`#version 300 es`, `layout ( location = 0 ) out vec4 oColor;`), SPIR-V diagnostics.
* `intl` date-format tables — `MONTHS`, `WEEKDAYS`, `QUARTERS`, `STANDALONEWEEKDAYS`, …
* `html`/`petitparser` parser messages — `Expected name`, `loopMerge`, `loopHeader`.

These reflect the older plugin versions bundled in 2.22 and carry no protocol or device meaning.

## Endpoint-level deltas (protocol-relevant, but these are *absence*, not unique-string)

| endpoint | 2.22 | 2.23 | 2.24 | 4.0.8 |
|---|:--:|:--:|:--:|:--:|
| `/dev/queryDefaultConfig` | ✅ | ✅ | ✅ | ❌ |
| `/dev/shareConfig` | ❌ | ✅ | ✅ | ✅ |
| `/dev/importShareConfig` | ❌ | ✅ | ✅ | ✅ |
| `/dev/queryGameList` | ❌ | ❌ | ✅ | ❌ |

Read: 2.22 **has** `queryDefaultConfig` (matching 2.23/2.24) and **lacks** the share endpoints that
2.23+ introduced. `queryGameList` is **not** a "later builds lost it" case — it exists **only in
2.24** and is absent even from 2.22. See `../version-diff/server-api-history.md`.

## Conclusion

The 2.22→later progression is one of **addition and renaming**, not removal of app protocol strings.
No 2.22-only string names an UNKNOWN field; the only 2.22-unique tokens with any meaning are the
device-label variants `RAINBOW` / `ArmorX Pro` and the dropped EN/JP ArmorX-Pro manual URLs.