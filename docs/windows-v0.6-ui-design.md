# Windows v0.6 UI/UX design notes

Status: **v0.6.0 release candidate**.

## Design direction

ArmorX Studio uses a dark-first glass/graphite interface with violet and cyan
status accents. Light mode uses the same hierarchy and spacing rather than a
separate layout.

The app is designed to remain usable from a compact 760px-wide window through
large ultrawide displays:

- sidebar collapses to icons on medium widths;
- navigation moves to a bottom strip at compact widths;
- editing grids collapse from 4/3/2 columns to one column;
- the persistent Apply dock keeps the safety state visible.

## Requested interaction features

Implemented in the initial v0.6 shell:

- dark/light toggle;
- About dialog;
- contextual question-mark help;
- system tray status;
- separate live Button Test;
- animated L3/R3 click state;
- analog LT/RT visual fill;
- drag/reorder macro timeline;
- macro key palette/chords;
- responsive design;
- user-facing pending-change and safety status.

## Evidence boundaries

Tooltips and visuals do not invent vendor percentages. Where a field has only a
recovered raw byte meaning, the help text recommends starting from the live
device baseline and labels the value as raw 0–255.

## Quality gates

The branch CI requires:

- TypeScript typecheck through the Vite build;
- Vitest macro-format tests;
- .NET Release compilation on windows-latest;
- self-contained publish;
- core self-test;
- WPF Release compilation;
- verification that bundled React assets are present;
- Playwright interaction and screenshot QA;
- packaged CI artifact with SHA-256.
