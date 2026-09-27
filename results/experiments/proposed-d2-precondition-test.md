# Proposed D2 Precondition Test

## Goal

Decide between the only two remaining protocol-level candidates: the **write type** of the D2
enable (write-without-response vs write-with-response) and a **CCCD re-arm after the enable**.

## Static evidence supporting the test

- The D2 toggle itself is PROVEN STATIC and byte-identical to what we already send.
- `write-without-response` is PROVEN STATIC for the 2.22/2.23 code path
  (`BleDeviceInteractor::writeCharacterisiticWithoutResponse` @ `0x4d0eb4`), but **UNKNOWN for the
  4.0.8 generation** that matches our firmware `2741`.
- In 2.22–2.24 the app issues the enable **before** the page owns a subscription; in 4.0.8
  notifications are armed at connect. Both orderings are represented here.

## Preconditions

- unit powered and advertising; D6 == `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`
  (the durable baseline; no experiment state may be present)
- primary network guard PASS; lab radio ownership resolved dynamically
- no configuration write planned

## Device starting state

Stock baseline configuration, no D2 mode active, link up.

## Exact TX sequence

1. connect; read `2A24`/`2A26` (identity gate) — read-only
2. `0B` link-health, expect `A5 05 0B 30 E5`
3. **variant A**: D2 enable `A5 05 D2 01 7D` with **write-with-response**; listen 20 s
4. **variant B**: while still in test mode, re-issue the CCCD write for `FFE2` (subscribe again);
   listen 20 s
5. **variant C**: D2 disable `A5 05 D2 00 7C`, re-issue the enable with write-without-response;
   listen 20 s
6. D2 disable; disconnect

## Expected replies

1. identity reads return `ZJ-XT` / `2741`
2. `A5 05 0B 30 E5`
3. either the D2 echo only (as today) or a 0x02 status stream
4/5. same criterion per variant

## Timing

20 s of listening per variant, with a 1 s flush before each so a stale frame cannot be mistaken for
a live one.

## Notification/subscription sequence

Variant B deliberately re-issues the CCCD write; variants A and C leave the connect-time
subscription untouched. The subscription state must be logged per variant.

## Operator action

ONE BUTTON ONLY.

> Power the unit on if it is off, and **press A twice**, then click DONE.

## Success criteria

A variant produces ≥5 `A5 12 02` frames within its window, including at least one frame while the
operator is not pressing anything (proving the stream, not just an echo).

## Failure criteria

All variants produce only the D2 echo → the write type and re-subscribe are eliminated, and the
root cause leaves the protocol layer.

## Abort criteria

Identity mismatch against the manifest; any unexpected configuration write; link loss mid-window;
or a D6 read differing from the baseline at the end.

## Cleanup

D2 disable, disconnect, then a read-only D6 confirming the unchanged baseline.

## Persistent-state risk

NONE. Only `D2` (test-mode toggle) and the CCCD write are used; no configuration, macro, DPI,
lighting, RCSP or firmware command is sent.

## Why this test is reversible

Test mode is a runtime toggle with a documented mirror frame, and it has been toggled repeatedly on
this unit today with the configuration unchanged; the CCCD write only affects the current
connection. A power cycle clears either.

## Commands explicitly prohibited

`D7` (config write), `D8` (commit), any DPI write, any lighting write, any RCSP/OTA command, any
firmware write.
