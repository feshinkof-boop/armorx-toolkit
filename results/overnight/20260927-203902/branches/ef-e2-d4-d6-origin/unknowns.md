# Unknowns & open questions

Everything below is *not* PROVEN STATIC from the 4.0.8 blutter dump alone. Each item lists what
was checked and what would settle it.

## 1. Identity of the shared singleton at static field index `0x678`
- Status: **INFERRED / UNKNOWN class**.
- Facts (PROVEN STATIC): `armorx_pro_root.dart:2590` (0xab8e20), `rainbow_root.dart:3874`
  (0xacee94), `rainbow_test.dart:1624` (0xacf774), `rainbow_tab_config_1s.dart:14476`
  (0xa8403c) all do `LoadStaticField(0x678)` → `obj.field_53` → `field_7` (a listener List) →
  append a closure and grow. The appended closures are typed `(dynamic, Duration)`
  (e.g. 0xab8fb4, 0xacf4cc, 0xacf874, 0xa84160), so the object exposes a `Stream<Duration>`
  (or equivalent notifier whose event is a Duration).
- Why unresolved: no `StoreStaticField(0x678)` and no `InitLateFinalStaticField` annotation
  for offset `0x678` appears anywhere in `blutter_out/asm/`. The real `export`/init site
  (or its named annotation string) is not in the dumped compilation units for moojiang.
- To settle: grep the raw `pp.txt`/`objs.txt` object table for the field-table slot 0xcf0
  (`0xcf0 = 2*0x678`), or scan the symbol string table for a `<Class>.<field>: static late final
  (offset: 0x678)` annotation. Also candidate is a top-level/`library-private` final not annotated
  in the disasm.

## 2. Why the Duration-typed callback never uses its Duration argument
- Status: **UNKNOWN (benign)**.
- The initState callbacks (0xa84160, 0xacf4cc, 0xab8fb4, 0xacf874) are typed as taking a
  `Duration`, but their bodies ignore it (they just call the request/subscribe methods).
- Likely the event is a "device connected, for duration D" / "ready after delay" signal, but
  the emitting side was not located. Behaviourally irrelevant to the request ordering.

## 3. Exact graph of D6 accumulation into the 144-byte config buffer
- Status: **STRONG EVIDENCE, not fully line-verified**.
- The A4-fragment branch (0x82699c) uses `subpackageLength()` @0x819190 and `replaceRange`
  @0x6f6ff4 to write each fragment at `(index-1)*subpkgLen`, and calls `parsingData` @0x8270b0
  once the byte count reaches the total (`written == total`, via the `fdiv`/`fcvtps` at
  0x826cc8). The exact per-fragment header layout (which byte is the fragment index) was not
  byte-for-byte decoded; only the accumulate-then-parse control flow is proven.
- To settle: decode `subpackageLength` @0x819190 and `parsingData` @0x8270b0 and diff against
  the captured eight 20-byte `A4 D6 ...` fragments and the 144-byte durable config.

## 4. Whether D4 reply stores the onboard mode anywhere beyond the debug print
- Status: **PARTIAL**.
- The `0xD4` branch (0x826ec8) prints `"板载mode = "` + `frame[4]` and reads `frame[4]` again at
  0x826f50, then jumps to setState. No `StoreField`/`StoreStaticField` for the mode value was
  observed in the branch — the storing site (if any) was not identified in this pass.

## 5. The `0x827f30` / `0x827c1c` follow-up closures
- Status: **UNKNOWN contents** (control-flow only).
- The `0x0E` ("保存指令结果") reply schedules a `Timer` → closure `0x827f30`, and the `0xD7`
  branch schedules `Future.delayed` → closure `0x827c1c`. `0x827f30` is *also* a caller of
  `getDeviceConfig` (0x8280dc). The precise bodies were not transcribed; treated as
  post-config-write refresh paths, which are **not** the pre-Button-Test D6 trigger.

## 6. Which page was foreground when the wire capture was taken
- Status: **UNKNOWN / out of scope**.
- Two independent init paths can each produce part of the sequence (device page
  `_ArmorXProWidgetState`/`_RainbowWidget` for EF/0B/E2; config tab
  `_RainbowDeviceConfig1sState` for D4/D6). The HCI/capture timing needed to say which fired
  first is explicitly out of scope (no HCI timing evidence used here).

## Non-unknowns explicitly checked (to prevent re-derivation)
- No A5-parser branch (opcode 0xEF/0x0B/0xE2) calls `getInputModel` or `getDeviceConfig`;
  the only `getInputModel`/`getDeviceConfig` call sites are the config-tab initState closure and
  the post-config-write response handlers. (grep of `bl #0xa84258` / `bl #0x80dbfc`.)
- The `0xEF` reply branch never emits E2 or D4/D6; it calls `onGetDeviceUUID` + `getZKMVer`
  (+ `getMTU`).
