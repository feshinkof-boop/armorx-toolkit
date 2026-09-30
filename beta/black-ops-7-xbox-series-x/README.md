# ArmorX Pro - Black Ops 7 / Xbox Series X Beta Pack

This beta pack contains three ArmorX Pro profiles for **Call of Duty: Black Ops 7 on Xbox Series X**, plus optional Macro Studio test files and the matching in-game settings.

## Download

Download the complete beta pack:

[ArmorX_BO7_SeriesX_Pack.zip](./ArmorX_BO7_SeriesX_Pack.zip)

For feedback, use [GitHub issue #12](https://github.com/feshinkof-boop/armorx-toolkit/issues/12).

## Start here

Use **`profiles/BO7_Competitive_Recommended.json`** first. It is the general-purpose profile and the best baseline for feedback.

| Profile | Rear buttons | Intended use |
| --- | --- | --- |
| **Competitive - Recommended** | M1=A, M2=X, M3=Y, M4=B | General multiplayer / ranked-style layout |
| **Rush - Movement First** | M1=A, M2=B, M3=X, M4=Y | Aggressive SMG and movement-heavy play |
| **Precision - AR** | M1=A, M2=X, M3=B, M4=Y | AR and accuracy-focused play |

The profile files change only the proven rear-button mapping bytes from the validated ArmorX baseline. They do **not** encode BO7 sensitivity, FOV, aim response curve, or BO7 stick deadzones; those must be entered in-game from `BO7_in_game_settings.json`.

## Before you begin

You need:

1. **ArmorX Studio v0.6.0 for Windows**.
2. An ARMOR-X Pro connected to the Windows PC through the normal supported connection path.
3. The official BIGBIG WON mobile app disconnected while ArmorX Studio is using the device.
4. Preferably firmware **2741 / model ZJ-XT**, which is the directly validated baseline for this pack.

ArmorX Studio automatically reads the live configuration, preserves unknown bytes, creates a pre-write backup, shows the exact diff, and verifies the final 144-byte configuration after writing.

## How to apply a profile in ArmorX Studio

### 1. Connect the ARMOR-X Pro

Open **ArmorX Studio** and click **Connect** in the top-right corner.

Wait until the Dashboard shows the controller as connected and a valid configuration has been loaded.

### 2. Import the beta profile

Open **Profiles** from the left sidebar.

Choose **Import** and select one of the JSON files from the `profiles` folder. For your first test, select:

`BO7_Competitive_Recommended.json`

The imported profile is stored locally in ArmorX Studio. Importing it does **not** immediately write anything to the controller.

### 3. Load the profile

Select the imported profile and choose **Load**.

ArmorX Studio loads the profile into the editor while keeping the controller unchanged until you approve the write.

### 4. Review the pending changes

Look at the pending-change indicator at the bottom of ArmorX Studio, then click **Review & Apply**.

For this beta pack, the expected functional changes are only the rear-button mappings plus the automatically recalculated CRC.

If you see unexpected changes to sticks, triggers, gyro, turbo, or unknown bytes, **cancel the write and report it**.

### 5. Apply and verify

In the review window, confirm the change list and choose **Apply & Verify**.

ArmorX Studio will:

1. re-read the live configuration,
2. create a full pre-write backup,
3. write the merged known changes,
4. persist the configuration,
5. read the controller back twice,
6. require both 144-byte verification reads to match the target.

Do not disconnect or power off the ARMOR-X Pro during this process.

### 6. Test the rear buttons

Use **Button Test** in ArmorX Studio before launching the game.

Expected output for the recommended profile:

- **M1 -> A** - Jump
- **M2 -> X** - Reload / Interact
- **M3 -> Y** - Weapon swap
- **M4 -> B** - Crouch / Slide / Dive

Then launch BO7 and enter the corresponding manual game settings from `BO7_in_game_settings.json`.

## Switching between profiles

Import all three JSON files once. After that, switch from the **Profiles** page by loading the profile you want and using **Review & Apply** again.

- **Competitive - Recommended:** general baseline.
- **Rush - Movement First:** movement-oriented rear-button ordering, paired with faster BO7 game settings.
- **Precision - AR:** accuracy-oriented rear-button ordering, paired with lower BO7 sensitivity/ADS settings.

The ArmorX profile itself does not change BO7 sensitivity. Change the in-game values manually when comparing Rush and Precision.

## How to restore your previous configuration

ArmorX Studio creates a backup before every successful write attempt.

To return to the configuration you had before testing:

1. Connect the ARMOR-X Pro.
2. Click **Restore backup** from the bottom action area.
3. Review the restore diff.
4. Choose **Restore & Verify**.

The app writes the saved original 144-byte image and verifies it twice.

## Macro Studio beta files

The `macros` folder contains timing experiments such as YY and Slide -> Jump variants.

To inspect one:

1. Open **Macro Studio**.
2. Choose **Import**.
3. Select a macro JSON file.
4. Review its steps and timings in the timeline.

**Important:** ArmorX Studio v0.6.0 Macro Studio is currently **offline-only**. It can import, edit, validate, and export these macro files, but it does **not yet install macros to the ArmorX hardware**.

Also follow the rules of the game/mode you are playing; automated inputs may be restricted by game or tournament rules.

## What beta testers should report

Please include:

- ArmorX model and firmware shown in the app.
- ArmorX Studio version.
- Xbox model.
- Which profile you tested.
- Whether import succeeded.
- Whether **Review & Apply** showed only expected mapping + CRC changes.
- Whether **Apply & Verify** completed successfully.
- Whether M1/M2/M3/M4 produced the expected buttons in Button Test.
- BO7 mode and weapon/playstyle used.
- Your BO7 sensitivity/FOV/deadzone values.
- Any stick drift, accidental presses, missed rear-button inputs, or uncomfortable mapping.
- Which profile you preferred and why.
- If something failed, attach ArmorX Studio diagnostics and a screenshot of the change review where possible.

Do **not** post Bluetooth addresses, serial numbers, account tokens, or other private identifiers.

## Validated pack baseline

The profile bytes were derived from the project's real-hardware validated ARMOR-X Pro baseline:

- Model: **ZJ-XT**
- Firmware: **2741**
- Baseline CRC: **0x2C40**
- Baseline SHA-256: `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`

The beta profiles intentionally preserve unrelated bytes from that baseline and modify the rear-button mappings plus the derived CRC.

## Pack integrity

Current ZIP SHA-256:

`9853e25c893bc25ac007580a21c46a84538c793eeda2518c93b6813740be5909`

The ZIP also contains `SHA256SUMS.txt` for its internal files.

Thank you for testing. Useful feedback is not just whether a profile "feels good" - tell us **what worked, what failed, and under what settings/playstyle** so the next revision can be evidence-driven.
