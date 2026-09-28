# Live protocol frame corpus (raw capture bytes)

Extracted by `tools/ble/parse_btsnoop.py` from every btsnoop under `results/experiments` and
`baselines/imported-research`. One row per protocol frame; no interpretation.

Total protocol frames: **1255**

| magic | opcode | count |
|---|---|---|
| a5 | 02 | 1163 |
| a5 | d2 | 54 |
| a5 | 0b | 32 |
| a5 | fc | 2 |
| a5 | ff | 2 |
| a5 | f7 | 2 |

Notes: the local host-side btsnoop captures contain **no A4 frames and no D6/D7/D8/D9 frames**;
the fragmented family appears only in the harness transaction log
(`results/experiments/physical-20260927-170455-noop-d7/raw-tx-rx.log`), and it is included in the
family model artifact. `fc` and `ff` each appear twice: one generic FF echo per FC request.
