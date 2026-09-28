# DPI / trigger callgraph (F7, F6, FC)

Read from the 4.0.8 disassembly (addresses recorded). Every edge is a real call/reference; nothing is inferred.

## Chain

```
notify.closure           --> ble.getDpi               calls (reply-triggered read)
notify.closure           --> ble.getStepLength        calls (chained read after the DPI read)
ble.getDpi               --> fw.gate                  reads
ble.getDpi               --> dev.gate                 reads
ble.getDpi               --> ble.write                writes
ble.getStepLength        --> ble.write                writes
ui.rainbow_more          --> gs.writeDpiConfig        onChanged(int)
ui.rainbow_more          --> gs.writeStepLengthConfig onChanged(bool) / onChanged(int)
ui.simulate              --> ble.getStepLength        _requestStepLength / _scheduleStepLengthRead
ui.simulate              --> gs.writeStepLengthConfig simulate path write
gs.writeDpiConfig        --> ble.write                writes
gs.writeStepLengthConfig --> ble.write                writes
gs.writeDpiConfig        --> fw.gate                  FC vs F6 selection
gs.writeStepLengthConfig --> fw.gate                  requires version >= 0x36
ble.write                --> dev.reply                device answer arrives as a notification
dev.reply                --> notify.closure           dispatch back into the notification handler
```

## Nodes

| id | kind | what | grade |
|---|---|---|---|
| `ui.rainbow_more` | UI | widgets/rainbow/rainbow_more.dart - settings page (DPI + step-length controls) | PROVEN STATIC |
| `ui.simulate` | UI | widgets/configV280/config_simulate_command.dart - command simulator (_requestStepLength, _scheduleStepLengthRead, _handleConfigEvent) | PROVEN STATIC |
| `notify.closure` | parser | [closure] (dynamic, List<int>) - notification handler; requests getDpi() then getStepLength() | PROVEN STATIC |
| `ble.getDpi` | encoder | BluetoothModel::getDpi @0x8b4e3c -> A5 05 FC 80 26 | A5 05 F6 80 20 | A5 04 F6 9F | PROVEN STATIC |
| `ble.getStepLength` | encoder | BluetoothModel::getStepLength @0x8b4d30 -> A5 04 F7 A0 | PROVEN STATIC |
| `ble.write` | transport | BluetoothModel::write @0x80dd28 - ATT write of the frame, called by every builder and writer | PROVEN STATIC |
| `gs.writeDpiConfig` | encoder | writeDpiConfig @0x946750 -> A5 05 FC|F6 <sel & 0x0F> <cks> | PROVEN STATIC |
| `gs.writeStepLengthConfig` | encoder | writeStepLengthConfig @0x9445d4 -> A5 07|08 F7 <flag> <lo> <hi> <cks> | PROVEN STATIC |
| `fw.gate` | gate | firmware-version gate: static field 0xb6c; 0x35 selects F6, 0x36 gates the F7 write | PROVEN STATIC |
| `dev.gate` | gate | device-model gate: four Instance_Device compares in getDpi (same model set as the earlier FC/F6 pass) | PROVEN STATIC |
| `dev.reply` | parser | reply envelope A5 05 FF FC A5 - opcode 0xFF, byte[3] echoes the queried opcode, zero payload | PROVEN LIVE |

## Pinned unknowns

- which received opcode triggers the getDpi()/getStepLength() pair (the handler branches on Smi-tagged values; the trigger is not yet pinned)
- whether any UI control immediately reads back a written value
- whether the device persists F7/FC writes (device-side; needs the deferred read-only D6 experiment)
- no edge to D2 bytes [15]/[16] exists in the binary - F7 is not connected to the trigger analog path by any code found

Diagram: `dpi-trigger-callgraph.dot` (`dot -Tsvg`).
