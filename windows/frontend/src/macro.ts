export const KEY_IDS: Record<string, number> = {
  A: 0, B: 1, X: 3, Y: 4, LB: 6, RB: 7, LT: 8, RT: 9,
  VIEW: 10, MENU: 11, GUIDE: 12, L3: 13, R3: 14,
  DPAD_UP: 16, DPAD_DOWN: 17, DPAD_LEFT: 18, DPAD_RIGHT: 19,
  M1: 23, M2: 24, M3: 25, M4: 26,
  L_LEFT: 34, L_RIGHT: 35, L_DOWN: 36, L_UP: 37,
  R_LEFT: 38, R_RIGHT: 39, R_DOWN: 40, R_UP: 41,
  L_LEFT_DOWN: 42, L_RIGHT_DOWN: 43, L_LEFT_UP: 44, L_RIGHT_UP: 45,
  R_LEFT_DOWN: 46, R_RIGHT_DOWN: 47, R_LEFT_UP: 48, R_RIGHT_UP: 49,
};

export const RUN_KEYS = { M1: 23, M2: 24, M3: 25, M4: 26 };
export const MODES = { long_press: 0, tap: 1, long_press_cycle: 2, tap_cycle: 3 } as const;
export const MAX_STEPS = 16;

export type MacroStep = { id: string; keys: string; duration: number; interval: number };
export type MacroDraft = {
  name: string;
  trigger: keyof typeof RUN_KEYS;
  mode: keyof typeof MODES;
  repeatTime: number;
  active: boolean;
  steps: MacroStep[];
};

export function normalizeKey(value: string) {
  return value.trim().toUpperCase().replaceAll("-", "_").replaceAll(" ", "_");
}

export function parseChord(expr: string) {
  const tokens = expr.split("+").map(normalizeKey).filter(Boolean);
  if (!tokens.length) throw new Error("Step needs at least one key.");
  const ids: number[] = [];
  const names: string[] = [];
  for (const token of tokens) {
    if (!(token in KEY_IDS)) throw new Error(`Unknown key: ${token}`);
    const id = KEY_IDS[token];
    if (!ids.includes(id)) {
      ids.push(id);
      names.push(token);
    }
  }
  return { ids, names };
}

export function validateMacro(draft: MacroDraft): string[] {
  const errors: string[] = [];
  if (!draft.name.trim()) errors.push("Macro name is required.");
  if (!(draft.trigger in RUN_KEYS)) errors.push("Trigger must be M1–M4.");
  if (!(draft.mode in MODES)) errors.push("Execution mode is invalid.");
  if (draft.repeatTime < 0) errors.push("Repeat time cannot be negative.");
  if (draft.steps.length < 1 || draft.steps.length > MAX_STEPS) errors.push("Macro must contain 1–16 steps.");
  draft.steps.forEach((step, index) => {
    try { parseChord(step.keys); } catch (error) { errors.push(`Step ${index + 1}: ${(error as Error).message}`); }
    if (step.duration < 0 || step.interval < 0) errors.push(`Step ${index + 1}: timing cannot be negative.`);
  });
  return errors;
}

export function buildMacroObject(draft: MacroDraft) {
  const errors = validateMacro(draft);
  if (errors.length) throw new Error(errors.join("\n"));
  const rows = draft.steps.map((step, index) => {
    const parsed = parseChord(step.keys);
    return {
      index,
      keyText: parsed.names.join("+"),
      mapList: JSON.stringify(parsed.ids),
      keyNameList: JSON.stringify(parsed.names),
      duration: Math.trunc(step.duration),
      interval: Math.trunc(step.interval),
      showUpLine: index !== 0,
      showDownLine: index !== draft.steps.length - 1,
      showInterval: index !== draft.steps.length - 1,
      showAdd: true,
    };
  });
  return {
    changed: true,
    id: -1,
    inUse: draft.active,
    runKey: RUN_KEYS[draft.trigger],
    runKeyName: draft.trigger,
    isRepeat: MODES[draft.mode],
    repeatTime: Math.trunc(draft.repeatTime),
    macroName: draft.name.trim(),
    macroJson: JSON.stringify(rows.map((row) => JSON.stringify(row))),
  };
}

export function draftFromMacroObject(obj: Record<string, unknown>): MacroDraft {
  const rowsOuter = JSON.parse(String(obj.macroJson || "[]")) as Array<string | Record<string, unknown>>;
  const rows = rowsOuter.map((row) => typeof row === "string" ? JSON.parse(row) : row);
  const trigger = String(obj.runKeyName || "M1") as keyof typeof RUN_KEYS;
  const modeEntry = Object.entries(MODES).find(([, value]) => value === Number(obj.isRepeat));
  const mode = (modeEntry?.[0] || "tap") as keyof typeof MODES;
  const draft: MacroDraft = {
    name: String(obj.macroName || "Imported Macro"),
    trigger,
    mode,
    repeatTime: Number(obj.repeatTime || 0),
    active: Boolean(obj.inUse),
    steps: rows.map((row, index) => ({
      id: crypto.randomUUID?.() || `import-${index}`,
      keys: (() => {
        const names = JSON.parse(String(row.keyNameList || "[]")) as string[];
        return names.join("+");
      })(),
      duration: Number(row.duration || 0),
      interval: Number(row.interval || 0),
    })),
  };
  const errors = validateMacro(draft);
  if (errors.length) throw new Error(errors.join("\n"));
  return draft;
}
