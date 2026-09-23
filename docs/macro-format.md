# ARMORX Pro macro format

## Overview

The ARMORX Pro macro model represents a macro as an outer object containing trigger/mode metadata plus a `macroJson` string. Captured V41 traffic shows that `macroJson` decodes to a `List<String>`, where each string is itself a JSON-encoded row object.

## Trigger buttons

| Trigger | ID |
|---|---:|
| M1 | 23 |
| M2 | 24 |
| M3 | 25 |
| M4 | 26 |

## Execution modes

| Value | Meaning |
|---:|---|
| 0 | Long press |
| 1 | Tap |
| 2 | Long press to cycle |
| 3 | Tap to cycle |

## Outer fields

- `inUse`
- `runKey`
- `runKeyName`
- `isRepeat`
- `repeatTime`
- `macroName`
- `macroJson`

## Row format

A decoded row looks like:

```json
{
  "index": 0,
  "keyText": "A+RT",
  "mapList": "[0,9]",
  "keyNameList": "[\"A\",\"RT\"]",
  "duration": 120,
  "interval": 70,
  "showUpLine": false,
  "showDownLine": true,
  "showInterval": true,
  "showAdd": true
}
```

`mapList` and `keyNameList` are themselves JSON strings inside the row object. Captured V41 traffic also shows `showAdd: true` on every serialized row, including non-final rows.

## Timing

The builder supports a hold duration and post-step interval in milliseconds.

A common default row is:

- hold: 200 ms
- interval: 100 ms

## DSL example

```text
@name Example Combo
@trigger M1
@mode tap
@repeat 200

A       80   50
X      100   60
B+RT   120   70
Y       90  100
```

Build it with:

```bash
python tools/armorx_macro.py build examples/example_macro.txt -o macro.json
```

Then inspect it:

```bash
python tools/armorx_macro.py inspect macro.json
```

## Joystick pseudo-keys

IDs `34..49` are used by the macro engine for joystick directions. Their current labels are marked **STRONG EVIDENCE** pending independent hardware validation.

## Limits

The current V41-era model supports up to 16 macro steps in the builder.

## Unknowns

Share/Screenshot is not assigned a macro key ID without direct verification. Firmware-internal frame encoding is intentionally separate from the portable macro JSON representation documented here.


## Captured V41 wire nesting

The captured client uses three serialization layers:

```text
HTTP JSON object
  -> macroJson: string
      -> JSON List<String>
          -> each string decodes to one row object
              -> mapList/keyNameList are JSON strings
```

For `/dev/addMacro`, captured traffic sends `inUse` as integer `0` or `1`. Share objects can carry the same logical field as a JSON boolean.
