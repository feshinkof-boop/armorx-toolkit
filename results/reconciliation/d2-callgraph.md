# D2 call graph (4.0.8, with cross-version notes)

```text
Button Test UI handler
  ↓
enable/start function
  ↓
frame builder
  ↓
BLE write (FFE1)
  ↓
notification callback (FFE2)
  ↓
dispatcher
  ↓
D2 branch (gate)
  ↓
button-event parser
  ↓
UI/state update
```

| node | function | build | address | grade |
|---|---|---|---|---|
| `UI_BUTTON_TEST` | _ArmorXProMoreWidgetState::build ListTile 按键测试 | 4.0.8 | `0x940684` | PROVEN STATIC |
| `UI_ROUTE` | Navigator.push(MaterialPageRoute -> RainbowTest) | 4.0.8 | `0x94773c` | PROVEN STATIC |
| `PAGE_INIT` | _RainbowTestState::initState callback | 4.0.8 | `0xacf744/0xacf874` | PROVEN STATIC |
| `ENABLE` | BluetoothModel::testModeSwitch(true) - frame builder | 4.0.8 | `0xabaef4` | PROVEN STATIC |
| `WRITE` | FFE1 write (write-without-response in 2.22/2.23; UNKNOWN in 4.0.8) | all | `FFE1` | PROVEN STATIC / UNKNOWN |
| `NOTIFY_ARM` | BluetoothModel::onCharacteristicChanged (FFE2 armed at connect) | 4.0.8 | `0xaca7c4` | PROVEN STATIC |
| `STREAM` | BroadcastStreamController -> page _BroadcastStream listen | 4.0.8 | `0xacf974/0xacf9a4` | PROVEN STATIC |
| `PARSER` | _RainbowTestState::analysisData | 4.0.8 | `0xacfa64` | PROVEN STATIC |
| `GATE` | frame[2]==0x02 gate (cmp w0,#4 = Smi 2) | 4.0.8 | `0xacfaac` | PROVEN STATIC |
| `MASK` | mask = bytes [3..6] big-endian, bit == key id | all | `0xacfad0-0xacfb88` | PROVEN STATIC |
| `STATE` | per-key booleans + setState on change | 4.0.8 | `state fields 0x117..0x177` | PROVEN STATIC |
| `DISABLE` | dispose -> testModeSwitch(false) | 4.0.8 | `0xadd7e0/0xadd844` | PROVEN STATIC |
