# Attempt 1 — VOID (harness fault, not an operator fault)

W0 captured 248 valid frames (bit 0 only, byte[16]=0 in all of them) — the control window was good.
W1 and W2 captured **nothing**, because the runner restarted `btmon` before every window:

    btmon attaches to the HCI *user channel*; cycling it while a BLE connection is live killed the link,
    so after W0 no notification ever reached the host again.

All four capture files are 383 bytes (btmon header only) — **no HCI coverage in this attempt**.
The operator performed all three windows correctly (ACKs 06:33:59 / 06:34:43 / 06:35:18); the windows
were lost on our side. Fixed before attempt 2: one capture started before the connection and never
restarted, per-window notification buckets, and an active 0B liveness probe between windows so a dead
link can never again masquerade as "no frames".
