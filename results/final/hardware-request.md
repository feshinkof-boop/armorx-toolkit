# Hardware request — ARMOR-X lab, radio phases 3+4

**The combo adapter you were going to be asked to plug in is already plugged in.** The RTL8723B combo
(`0bda:b720`, Realtek, Wi-Fi N + BT 4.0) is attached at physical USB path **1-8** on this machine right now —
Wi-Fi netdev `wlxe84e068af1ff` on interface `1-8:1.2` (`rtl8xxxu`), Bluetooth controller `hci1` with BD
address `E8:4E:06:8A:F2:00` on `1-8:1.0`/`1-8:1.1` (`btusb`), firmware loaded (`rtl_bt/rtl8723b_fw.bin`,
fw version `0x0e2f9f73`) — so nothing needs to be inserted to proceed; please instead **confirm whether you
plugged it in yourself (and when) or whether it was already there and you were unaware**, and report back:
(a) the LED behaviour — is there a power/activity LED on the dongle, and is it solid, blinking slowly
(idle), or blinking fast (traffic), which distinguishes "idle but enumerated" from "doing radio work";
(b) whether it is plugged directly into a rear-panel port or via a hub/extender, since identity is bound to
the physical USB path `1-8` and any move to another port of a hub will change that path and therefore change
the anchor key in `baselines/radio/combo-adapter.json` (in that case re-run
`automation/radio/capture-radio-baseline.sh` while the adapter is in its final position); and (c) anything you
notice about the transverse side effect to watch for — the dongle's Wi-Fi radio is currently **isolated**
(NetworkManager-unmanaged + link down) precisely because NetworkManager otherwise keeps trying to associate it
with the neighbouring AP `K&M New 2.4`; if you want it back under NetworkManager run
`automation/radio/radio-restore.sh`, and if you want it isolated again run
`automation/radio/disable-combo-wifi.sh`. Finally, if you intend to use a *different* spare adapter for the
lab (or a second identical RTL8723B), say so before it is inserted, because two identical `0bda:b720` dongles
cannot be told apart by VID:PID alone — the tooling would then bind on USB port path, and I need to know which
port is meant to be the lab one.
