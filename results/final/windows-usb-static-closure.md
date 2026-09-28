# Windows / DevMgr / USB static closure (Part B)

Static only, 2026-09-27/28 overnight shift. No USB device was attached and none was needed: the
settled facts below come from artifacts captured earlier and are re-stated with their sources, and the
open items are graded by what a *static* pass can still achieve versus what now needs hardware.

## Settled facts (carried forward, sources in the project tree)

| fact | value | source |
|---|---|---|
| device identity | `VID_413D & PID_2106`, present in the registry with 3 instances under `Enum\\USB` | `armorx_research/dongle_baseline_v13/software/reg_413d2106.json` |
| HID shape | Usage Page `FF7A`, Usage `0001`, logical N = 64, Windows buffers 65 bytes including the report-ID byte, report ID in slot 0 | `dongle_baseline_v13` HID registry dumps + the HID capability artifacts |
| IN model | persistent / pre-posted IN |
| host backend | IOCP, `CreateIoCompletionPort` |
| packet conversion | `CUsbCmd::ToPacket` / `FromPacket`; `request+0x10` aliases `transfer_base+0x68` |
| device-type numbering | **two independent numbering systems** coexist and collide at values 5-7: `t_BBW_DevType` (per-class `GetDevType`/`GetBBWDevType`) and `t_ProductType` (switched at `0x1003212f`, used by `CDeviceUDisk::GetDeviceName`) | `armorx_research/devmgr_static/devmgr_device_type_map.json` |
| E2 reply parsing | the parser matches `0xA5`, reads the length at `+1`, branches on the opcode at `+2` - so an **E2 reply** is parsed on the same path as other short replies | `getmode_final_static_closure/final_static_closure_pass3.md` |

## Open items, graded

| item | status after this pass | what would move it |
|---|---|---|
| read symmetry (does every operation have a read counterpart?) | **UNKNOWN** - the operation tables are per-class virtuals and no complete table was reconstructed | a focused pass enumerating each class's vtable entries (static, possible) |
| buffer ownership across aliased transfers | **UNKNOWN** - `request+0x10` aliases `transfer_base+0x68`, but which layer frees the buffer was not established | static dataflow from the IOCP completion handler back to the allocator (static, possible) |
| wrapper operation tables | **PARTIAL** - per-class virtuals identified, not exhaustively listed | same as above |
| mark/model classifier | **PARTIAL** - the two numbering systems are separated and their collision documented; the string cross-references are catalogued | static xref of `devmgr_product_string_xrefs.json` against the classifier switch (static, possible) |
| E2 "normal path" | **PARTIAL** - the reply parse path is identified | static trace from the parse to the state assignment (static, possible) |
| why the current Assistant leaves the ARMORX legacy type inaccessible | **UNKNOWN** | needs the two numbering systems mapped to the UI's device list (static, possible) then a hardware confirmation |
| latent ArmorX Pro "factory" path | **UNKNOWN** | static search for factory/DFU entry strings (`devmgr_dfu_analysis.json` exists as a starting point) |
| normal vs Xbox-compatible re-enumeration | **UNKNOWN** | this is fundamentally a **hardware** question: re-enumeration is a device behaviour. Static code can only predict which descriptors it would request |

## Honest limit

Everything in the "what would move it" column that says *static, possible* is real work that was NOT
done tonight: it needs a proper PE xref pass over `DevMgr.dll` (the binary is present at
`armorx_research/devmgr_static/DevMgr.dll` with PE metadata already extracted), and it is scheduled as
its own branch rather than claimed here. What this document does is close the consolidation, separate
the two numbering systems that would otherwise be conflated, and mark the re-enumeration question as
hardware-bound rather than static.
