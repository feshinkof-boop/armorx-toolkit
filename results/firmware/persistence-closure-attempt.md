# ArmorX persistence closure attempt (V41, static)

* **0x3003ec call sites in the whole image: 1** (only `0x1e069d4`, inside `0x1e069c2`).

## dirty_flag_xrefs

```json
{
 "writer": [
  {
   "addr": "0x1e05cae",
   "instr": "[r0 + 0x1b4] = r1",
   "value": "3",
   "in_function": "0x1e05c66 (record writer)",
   "note": "executed immediately after the record header CRC is stored"
  }
 ],
 "other_writes_into_the_same_state_block": [
  {
   "addr": "0x1e0062e",
   "instr": "[r8 + 0x1b4] = r0",
   "value": "0x1fa0",
   "context": "initialiser that also writes [r8+0x1b0] = 0x1fa0 (five-iteration loop) - a default/sentinel store, base register for r8 not proven to be 0x4850"
  }
 ],
 "reader": [
  {
   "addr": "0x1e0684c",
   "instr": "r0 = [r5 + 0x1b4]",
   "in_function": "0x1e06842",
   "base": "0x4850 loaded at 0x1e06846 - PROVEN",
   "then": "r1 = [r5+0x1c4]; r0 |= r1; if (r0 != 0) -> 0x1e06994"
  }
 ],
 "meaning_of_3": "NOT a proven dirty level. The only proven consumer ORs state+0x1b4 with state+0x1c4 and takes an early-out; the function 0x1e06842 references dev_type diagnostics and is called from the dispatcher, the USB-host gamepad report builders (0x1e096b4, 0x1e09ad4, 0x1e09ce0) and 0x1e0aff2. Calling value 3 a 'dirty level' or 'pending record count' is NOT supported by the code read so far."
}
```

## library_module

```json
{
 "call_sites_into_0x1f0000_0x31ffff": 1324,
 "distinct_targets": 1300,
 "nearest_known": "0x301148 memset-like (record writer), 0x306b64/0x306c1a/0x306b06 at startup, 0x300970/0x30095a/0x300906/0x3008a0 (builder), 0x3003ec (config save)",
 "conclusion": "The app links against an out-of-image vendor library of at least ~100 KB with over a thousand call sites. Its bytes are absent from app.bin, the SDK rom.lst (0x100000-0x106fff), cpu/bd19/maskrom_stubs.ld (0x106xxx only) and p11_code.bin (4096 B). 0x3003ec remains unnamed and its internals unobservable."
}
```

## usbh_finding

```json
{
 "addresses": [
  "0x1e096b4",
  "0x1e09ce0",
  "0x1e09ad4"
 ],
 "evidence": "strings 'd, usbh_gamepad_ready= %d, usbh_gamepadp = %p' are referenced inside 0x1e096b4 and 0x1e09ce0; all three build frames via 0x1e0642c and consume [0x4850+0x1b4] via 0x1e06842",
 "grade": "STRONG EVIDENCE that this family emits USB-host gamepad reports",
 "consequence": "[state+0x1b4] may belong to the USB/2.4G report path rather than to the BLE config-flush path. The persistence chain must not assume otherwise."
}
```

## fw_u_032

```json
"UNRESOLVED - boundary stated. Identity unavailable; behaviour limited to 'submits a 144-byte config descriptor to an out-of-image vendor service, with a mode byte' (STRONG EVIDENCE for that much)."
```

## fw_u_033

```json
"OPEN - no timer, task, idle, power or disconnect hook reaching the dirty shadow was found in this window. Searches performed: alarm/timer words and the resolved call graph of the three storage functions. Next: enumerate callers of the flush-shaped library targets (0x3003ec has none but 0x3004xx-0x3005xx do) and cross-reference with an SDK timer API name once one is matched."
```

## Not advanced in this window

- D2 report builder/send gate
- macro ingress
- FC/F6/F7 state handling
- cross-version
- dongle V3600
- USB/2.4G packet evidence
- second MCU
