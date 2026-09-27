# Official app workflow (4.0.8) vs current harness

## STEP 01
UI EVENT: user opens 按键测试 from the ARMOR-X Pro "more" page
FUNCTION: _ArmorXProMoreWidgetState::build ListTile onTap closure
ADDRESS: 0x940684 (ListTile string) / 0x94773c (closure) / 0x947674 (route builder)
STATE BEFORE: BLE connected; notifications already armed on FFE2 by BluetoothModel
ACTION: Navigator.push(MaterialPageRoute -> RainbowTest)
TX: none
EXPECTED RX: none
STATE AFTER: _RainbowTestState constructed
DELAY: none
EVIDENCE: PROVEN STATIC
NOTES: this is the ARMOR-X Pro page - same product line as our unit

## STEP 02
UI EVENT: page initState
FUNCTION: _RainbowTestState::initState callback (registered @0xacf744, runs @0xacf874)
ADDRESS: 0xacf8cc
STATE BEFORE: connected, notify armed
ACTION: BluetoothModel::testModeSwitch(true) - issued asynchronously, NOT awaited
TX: A5 05 D2 01 7D on FFE1
EXPECTED RX: the device's 5-byte echo (which the parser will reject - see STEP 04)
STATE AFTER: test mode requested
DELAY: none (the 500 ms Duration in this page belongs to the disconnected re-render)
EVIDENCE: PROVEN STATIC
NOTES: builder @0xabaef4; checksum hard-coded

## STEP 03
UI EVENT: same initState, immediately after STEP 02
FUNCTION: _RainbowTestState::subscribeCharacteristic
ADDRESS: 0xacf8dc / listen @0xacf9a4
STATE BEFORE: notify already armed at connect
ACTION: wrap the connect-time broadcast stream and listen
TX: none (no CCCD write here in 4.0.8)
EXPECTED RX: status frames
STATE AFTER: listening
DELAY: none
EVIDENCE: PROVEN STATIC
NOTES: in 2.22/2.23/2.24 this step performs the actual subscription and it happens AFTER the enable

## STEP 04
UI EVENT: notification arrives (device echo or status frame)
FUNCTION: _RainbowTestState::analysisData
ADDRESS: 0xacfa64 (gate @0xacfaac)
STATE BEFORE: listening
ACTION: gate frame[2]==0x02; on match extract bytes [3..6] big-endian as the key mask
TX: none
EXPECTED RX: 18-byte status frame
STATE AFTER: keyboard state booleans updated; setState only on change
DELAY: none
EVIDENCE: PROVEN STATIC
NOTES: the 5-byte D2 echo is discarded here purely because frame[2]=0xD2

## STEP 05
UI EVENT: user leaves the page
FUNCTION: _RainbowTestState::dispose
ADDRESS: 0xadd7e0 / 0xadd844
STATE BEFORE: connected
ACTION: cancel the Dart listener, then testModeSwitch(false)
TX: A5 05 D2 00 7C
EXPECTED RX: echo
STATE AFTER: test mode off
DELAY: none
EVIDENCE: PROVEN STATIC

### OFFICIAL APP
```text
UI (按键测试)
→ (notify already armed at connect)
→ D2 ENABLE (not awaited)
→ Dart listener
→ status frame
→ gate frame[2]==0x02
→ mask bytes [3..6] BE, bit == key id
→ setState
→ dispose: cancel listener
→ D2 DISABLE (if connected)
```

### CURRENT HARNESS
```text
CONNECT (+ subscribe FFE2)
→ 0B link-health (NOT sent by the app)
→ D2 ENABLE
→ listen
→ NO EVENTS
→ D2 DISABLE
```

### FIRST POINT OF DIVERGENCE
`FIRST POINT OF DIVERGENCE: UNKNOWN`

No divergence in the protocol sequence could be proven. The only proven difference is the extra
`0B` link-health query our harness sends (the app sends none), which is a read-only query and is
INFERRED to be harmless; and the write type used for the enable is UNKNOWN for 4.0.8 while our
harness uses write-without-response.
