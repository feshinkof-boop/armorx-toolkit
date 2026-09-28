# JieLi / firmware static work (Parts K and L)

Static only. This document separates **generic JieLi platform facts**, **ArmorX-proven facts**, and
things that are simply **not present in any artifact we hold**. It supersedes nothing: the detailed
fingerprint work remains `results/final/jieli-rcsp-verdict.md`, and this records what the overnight
shift found on top of it.

## What is proven, and how

| statement | grade | evidence |
|---|---|---|
| The Android app (all four builds) contains **no RCSP client** | PROVEN STATIC | no `AE00/AE01/AE02` UUID, no `FEDCBA`, no `com.jieli`/`jl_bt_ota`/`jl_ota` in any build |
| The **real unit exposes AE00/AE01/AE02** after connect + service discovery | **PROVEN LIVE** | GATT dump of the physical unit (`results/final/real-gatt-services.json`) |
| The unit's **configuration** conversation is **not** RCSP | PROVEN LIVE | the whole A5/A4 conversation runs on the custom service's FFE1 (write) / FFE2 (notify) |
| The **vendor Windows updater** carries a **JieLi AC632N `.ufw` upgrade library** | PROVEN STATIC | `DevMgr.dll` / `BTUpgrade*.dll` analysis in `armorx_research/` |
| The **body MCU** is AC6321A / AC632N / BD19 | **STRONG EVIDENCE - not proven** | inferred from the RCSP-capable stack plus the vendor updater; **no firmware dump exists**, so the exact part stays UNKNOWN |

## What the overnight shift adds

1. **No firmware package exists anywhere in the local artifacts.** A tree-wide search for `*.ufw`,
   `*.fw`, `*.ota`, `jl_isd`, `uboot.boot` returned no firmware image - the only `.bin` files are our
   own configuration readbacks and a captured device log. So **Part L's "analyse locally available
   packages on copies" has no subject**: there is nothing to analyse locally, and no copy was needed.
2. **The app contains no firmware download path.** Searching the 4.0.8 strings for `rcsp`, `jl_ota`,
   `jl_bt_ota`, `jieli`, `AC63*`, `authkey`, `procode`, and OTA-ish URLs found only library noise
   (`rotation*`). **No firmware metadata, no version API, no download URL, no signature or container
   description is present in the Android app.** The update toolchain is on the **Windows** side.
3. Therefore the firmware work splits cleanly:
   - **Android side**: nothing to find. Recorded as a proven negative so no future pass re-searches it.
   - **Windows side**: the `.ufw` upgrade library exists inside the vendor DLLs; analysing its
     container/signature handling is a legitimate static task (out of scope tonight - it needs a
     dedicated PE pass over `BTUpgrade*.dll`).
   - **Device side**: a firmware dump cannot be obtained statically at all.

## Generic JieLi facts (not to be conflated with ArmorX-proven ones)

The RCSP service layout (`AE00` service, `AE01` write, `AE02` notify), the `.ufw` package format, and
the `jl_*` tooling (`jl-misctools`, `jl-uboot-tool`, community `ghidra-jieli`, `AC632Nuke`) are facts
about the **platform family**. None of them is evidence about the ARMOR-X Pro's own firmware revision
or command set, and none is used here to claim anything device-specific. The device-specific evidence
stops at: *this unit speaks RCSP-capable service layout, and its settings are configured through a
non-RCSP custom service*.

## Explicit non-actions (safety)

No OTA, no firmware write, no bootloader interaction, no flash operation, no authentication bypass was
performed or proposed. Nothing in this document creates a path to writing firmware; it records that the
material to do so is not present locally, and that the only known update toolchain is a Windows vendor
library whose internals were not exercised.
