# Verdict

## Classification

**CASE 6 — none succeed.**

```text
C0 (harness control, write without response) : 0 valid frames
A  (write WITH response, ATT-verified)        : 0 valid frames
B  (explicit CCCD renewal after enable)       : 0 valid frames
C  (disable + re-enable on the same link)     : 0 valid frames
```

## What this refutes (each with live evidence)

1. **ATT write semantics (hypothesis A) — REFUTED.** Variant A's enable was proven at ATT level to
   be a `Write Request (0x12)` with a `Write Response (0x13)` (`t=127.263`), i.e. genuinely
   write-with-response, and the device replied with **only the 5-byte echo**. The write type does
   not change the outcome. (Official 4.0.8 static write type stays `UNKNOWN` — this experiment
   cannot and does not settle it.)
2. **Notification / CCCD state (hypothesis B) — REFUTED.** An explicit unsubscribe→resubscribe of
   FFE2 immediately after the enable (`cccd_renew_start` 35.478 s → `cccd_resubscribe_done`
   36.500 s, with `0000`/`0100` CCCD writes visible in the ATT capture) still produced nothing.
3. **Same-connection state transition (variant C) — REFUTED.** Enabling, disabling, then re-enabling
   on the same link produced only echoes (5 of them), no stream.

## What it leaves

**D2-U-007 remains UNKNOWN.** The harness already performs precisely the reconstructed official
sequence (modulo the extra `0B` link-health query), and none of the protocol-level candidates
explains the silence. This is a live confirmation of the static conclusion, not a new mystery:
the official workflow contains no step we omit.

Hypothesis C (harness orchestration) is *not* refuted by this experiment, because C0 — the exact
current harness behaviour — was itself silent: the harness behaves identically whether driven by
Bumble or by BlueZ/Bleak, which makes a Bleak-vs-Bumble artifact unlikely but does not exonerate
orchestration as a class.

## Next evidence target (not another guessed command)

An **official-app-vs-harness connection/session differential**:

1. capture the official Android app talking to this same unit (HCI snoop on the phone, or the app
   driven against an emulated peripheral) and compare its *connection lifecycle* with ours:
   pairing/bonding state, encryption, connection parameters (interval/latency/supervision timeout),
   MTU, and whether the phone's link stays up for as long as ours does;
2. compare the device's behaviour when a *bonded, encrypted* link exists versus our unbonded,
   unencrypted one — every harness run so far has been unbonded;
3. only then consider device-side state (the unit's own input-reporting gate), which is the one
   layer no static analysis of the app can reach.

No undocumented command should be invented in the meantime; the brief's rule stands.

## Configuration integrity (post-experiment)

D6 read after the experiment: `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`
→ **CONFIG_BASELINE_MATCH**.

Wording kept exact: this is a **readback integrity confirmation** after runtime-only work, **not** a
new durability proof. The baseline remains **DURABLE_OK** from the earlier
`write → readback → idle/settle → power cycle → D6 exact match` procedure. Immediate readback on
its own would only ever be **STAGED_OK**; nothing here changes that rule.
