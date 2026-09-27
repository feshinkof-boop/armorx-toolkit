# Operator UI validation — one-shot click-acknowledged dialogs

**Verdict: VALIDATED (operator click returned ACK programmatically; chat was not used).**

## What replaced the old alert

The previous repeating popup+sound alerter (`automation/physical-action-alert.sh`) is
**retired** and is no longer the interaction channel. Its failure mode is recorded in
`results/runtime/physical-alert/ALERT_PREVIOUS_VALIDATION.txt` (`ALERT_PREVIOUS_VALIDATION = INVALID`).

| Old (retired) | New |
|---|---|
| notify-send / kdialog popup recreated by a supervisor loop | ONE PySide6 window, created once |
| sound every 20 s until chat reply | ONE sound at window show, never repeated |
| acknowledgement = typing `DONE` in chat | acknowledgement = **clicking a button in the window** |
| action could be "advanced" on a timer | nothing advances without a click |

## Implementation

- `automation/operator_action_gui.py` — the dialog (PySide6 6.11.2, isolated venv `.venv-operator-ui`).
  - window title/header: `ARMOR-X ACTION REQUIRED` (per-request override allowed)
  - `WindowStaysOnTopHint`, `show()` + one `raise_()`/`activateWindow()` — no focus-stealing loop
  - no timers, no re-creation, no timer-based dismissal
  - sound: `pw-play automation/armorx-alert.wav`, started **once** in `play_once()`; `--sound-loop` is
    explicitly **refused** (exit 3) so the retired repetition cannot creep back
  - **the ack JSON is written only from the button's clicked handler** — not on window creation,
    not from a screenshot, not from a shell exit code
- `automation/request_physical_action.py` — the requester Hermes calls.
  - refuses if an ack for that ACTION_ID already exists (one action at a time)
  - launches the dialog **inside the live Plasma session** via `automation/run-in-plasma-session.sh`
  - blocks on the atomic ack file, prints the ack as JSON, exit `0` ACK / `1` CANCEL / `2` TIMEOUT / `3` usage
- Ack file: `results/runtime/operator-actions/<ACTION_ID>.json` (written with `mkstemp` + `fsync` + `os.replace`, so a reader never sees a partial file)
- Ledger: `results/runtime/operator-actions.jsonl` (`requested` / `acknowledged` / `timeout` events)

## Proof of the test that the operator ran

Requested 2026-09-27T17:42:19-04:00, clicked 2026-09-27T17:42:28.687435-04:00:

```json
{
 "status": "ACK",
 "action_id": "operator_ui_test",
 "response": "confirm_test",
 "clicked_at": "2026-09-27T17:42:28.687435-04:00",
 "pid": 208198,
 "title": "ARMOR-X OPERATOR UI TEST",
 "gui": "PySide6"
}
```

- The waiter process returned exit code `0` **and** this JSON — the value came from the click handler.
- `logs/operator-gui.log` shows exactly one `shown` line and one `clicked` line for `operator_ui_test`
  (the only other line is the earlier no-sound visibility smoke check).
- Sound backend for the test: `pw-play` (recorded in the log). One `Popen`, therefore one playback.
- No chat message was used to acknowledge: the operator never typed `DONE`/`ALERT TEST OK` for this test.

## Visibility proof

`results/runtime/operator-ui-proof/ui-smoke.png` — 3440x1440 screenshot of the live Plasma desktop
showing the dialog above all windows with the message text and its button row. (Screenshot proves
visibility only; it is the click that proves acknowledgement.)

## Caveats (stated plainly)

- Whether the sound was **audible** is not provable from this side; the log proves the command was
  launched exactly once with `pw-play` on the live session's PipeWire. Per the new rules the popup
  is authoritative if audio hardware is silent.
- The retired alerter's scripts remain in the tree for provenance but nothing calls them any more.
