import { describe, expect, it } from "vitest";
import { buildMacroObject, draftFromMacroObject, parseChord, validateMacro, type MacroDraft } from "./macro";

describe("macro format", () => {
  it("encodes the captured V41 list-of-JSON-strings shape", () => {
    const draft: MacroDraft = {
      name: "Combo",
      trigger: "M2",
      mode: "tap_cycle",
      repeatTime: 250,
      active: true,
      steps: [
        { id: "1", keys: "A", duration: 80, interval: 50 },
        { id: "2", keys: "B+RT", duration: 120, interval: 70 },
      ],
    };
    const obj = buildMacroObject(draft);
    expect(obj.runKey).toBe(24);
    expect(obj.isRepeat).toBe(3);
    const outer = JSON.parse(obj.macroJson);
    expect(typeof outer[0]).toBe("string");
    expect(JSON.parse(outer[1]).mapList).toBe("[1,9]");
  });

  it("round trips ordinary chords", () => {
    const original: MacroDraft = {
      name: "Roundtrip",
      trigger: "M1",
      mode: "tap",
      repeatTime: 200,
      active: false,
      steps: [{ id: "1", keys: "LB+RB", duration: 90, interval: 10 }],
    };
    const decoded = draftFromMacroObject(buildMacroObject(original));
    expect(decoded.name).toBe("Roundtrip");
    expect(decoded.steps[0].keys).toBe("LB+RB");
  });

  it("refuses unresolved key names instead of guessing", () => {
    expect(() => parseChord("SHARE")).toThrow(/Unknown key/);
  });

  it("caps V41 macros at 16 steps", () => {
    const draft: MacroDraft = {
      name: "Too long",
      trigger: "M1",
      mode: "tap",
      repeatTime: 100,
      active: false,
      steps: Array.from({ length: 17 }, (_, i) => ({ id: String(i), keys: "A", duration: 10, interval: 10 })),
    };
    expect(validateMacro(draft)).toContain("Macro must contain 1–16 steps.");
  });
});
