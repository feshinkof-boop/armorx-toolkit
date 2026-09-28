# Verdict — official vs harness session differential

## 1. Status: **PARTIAL**

| stage | state |
|---|---|
| harness session (Linux/Bleak + btmon) | **COMPLETE** — captured, decoded, timestamped |
| official-app session (Android) | **NOT CAPTURED** — see `official-session/raw/CAPTURE_UNAVAILABLE.txt` |

## 2. Why the official half is missing

`ANDROID_HCI_CAPTURE_UNAVAILABLE`.

- The phone is reachable on the network (`v2304a` 100.115.227.84, tailscale pong 124 ms) but has
  **no ADB transport**: `adb devices` empty, ports 5555/37000/40001 refused, `adb mdns services`
  empty, no phone on USB.
- One modal operator dialog asked for USB debugging + Bluetooth HCI snoop log; it was acknowledged
  at 19:09:22, and ADB still had no transport afterwards.
- The popup was **not** repeated (per the interaction contract).
- No root bypass, no security-setting change, nothing installed or removed.
- Prior Android work in this repo used an **emulator**, which cannot host a real BLE session with
  the physical unit, so it is not a substitute.

Consequently the official-side values (bond state, encryption, connection parameters, PHY, MTU,
CCCD timing, pre-D2 writes, D2 ATT opcode, idle `A5 12 02` count, A-button result, D2 disable
behaviour) are recorded as **NOT_CAPTURED / UNKNOWN** — not guessed.

## 3. What the harness session adds

First fully timestamped harness control session on the current code path:

```text
CCCD subscribe (handle 0x0078 = 0100)
0B query   a5040bb4        t=25.012  -> reply a5050b30e5            t=25.033
D2 OFF     a505d2007c      t=27.017  -> echo                          t=27.049
D2 ENABLE  a505d2017d      t=28.521  ATT Write Command (0x52) -> echo t=28.543
(idle 10 s)
D2 OFF     a505d2007c      t=38.531  -> echo                          t=38.554
Disconnect Complete                                                   t=42.147
```

Link: role **Central**, peer address type **Public**, interval **7.50 ms**, latency **0**,
supervision timeout **2000 ms**, ATT MTU negotiated **64** (server 64 / client 517),
one `LE Connection Update` at t≈24.9 s. Security: **no pairing, no SMP, no encryption** — the link
is unbonded and unencrypted.

Valid `A5 12 02` frames: **0** (as in every previous run). The only notifications were the 0B reply
and the three D2 echoes.

## 4. Earliest proven material difference

**UNKNOWN — not computable.** With no official capture, no stage-by-stage difference can be proven.
One harness-side extra is recorded as an observation about *our* side only
(`HARNESS_EXTRA_WRITE_D2_PRECLEAR`: we send D2 OFF before the enable; the reconstructed official
workflow showed no such pre-clear). It is explicitly **not** labelled `MISSING_PRECONDITION`.

## 5. Hypothesis status

- **D2-U-008** (bonding/encryption prerequisite): **UNKNOWN / untested** — the harness link is
  confirmed unbonded and unencrypted; whether the official app's is bonded is not observable
  without the capture. Neither supported nor refuted.
- **D2-U-009** (MTU / PHY / connection-parameter / link-lifetime differences): **partially
  narrowed, still UNKNOWN** — the harness numbers are now measured (7.50 ms, latency 0, 2000 ms,
  MTU 64); the official numbers are not captured, so no difference is asserted. PHY is not even
  reported by this adapter's capture.
- **D2-U-007** (why D2 stays silent): **still UNKNOWN**, and unchanged by this run — the harness
  remains silent exactly as before. **Not** upgraded to a harness divergence, because the official
  behaviour is unobserved.

## 6. Configuration

D6 read after the work: `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **CONFIG_BASELINE_MATCH**.
This is a readback integrity confirmation, **not** a new durability proof: the baseline remains
**DURABLE_OK** from the earlier `write → readback → idle/settle → power cycle → D6 exact match`
procedure. Immediate readback alone is still only **STAGED_OK**.

## 7. What would unblock this

A working ADB transport to the phone (USB debugging authorized, or wireless debugging + pairing),
then re-run the same brief unchanged: capture the official session, and only then compute the
staged differential. No new or undocumented protocol command is needed or proposed.
