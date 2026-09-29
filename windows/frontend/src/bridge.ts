import type { GamepadSnapshot, StudioState } from "./types";

type Message = {
  type: "response" | "event";
  id?: string;
  ok?: boolean;
  result?: unknown;
  error?: string;
  event?: string;
  payload?: unknown;
};

type Listener = (payload: unknown) => void;

const pending = new Map<string, { resolve: (value: unknown) => void; reject: (reason?: unknown) => void }>();
const listeners = new Map<string, Set<Listener>>();
let counter = 0;

const webview = (window as unknown as {
  chrome?: {
    webview?: {
      postMessage: (value: unknown) => void;
      addEventListener: (name: string, handler: (event: { data: Message }) => void) => void;
    };
  };
}).chrome?.webview;

if (webview) {
  webview.addEventListener("message", ({ data }) => {
    if (data.type === "response" && data.id) {
      const item = pending.get(data.id);
      if (!item) return;
      pending.delete(data.id);
      if (data.ok) item.resolve(data.result);
      else item.reject(new Error(data.error || "ArmorX Studio request failed"));
      return;
    }
    if (data.type === "event" && data.event) {
      listeners.get(data.event)?.forEach((listener) => listener(data.payload));
    }
  });
}

export const bridge = {
  native: Boolean(webview),
  invoke<T = unknown>(action: string, payload: Record<string, unknown> = {}): Promise<T> {
    if (!webview) return mockInvoke(action, payload) as Promise<T>;
    const id = `req-${Date.now()}-${++counter}`;
    return new Promise<T>((resolve, reject) => {
      pending.set(id, { resolve: resolve as (value: unknown) => void, reject });
      webview.postMessage({ id, action, payload });
    });
  },
  on(event: string, listener: Listener): () => void {
    const set = listeners.get(event) || new Set<Listener>();
    set.add(listener);
    listeners.set(event, set);
    return () => set.delete(listener);
  },
};

const zeroFields = {
  motorSpeedIdx: 2,
  motorMax: 180,
  triggerMode: 0,
  triggerLeftDeadzoneCenter: 8,
  triggerLeftDeadzoneSide: 245,
  triggerRightDeadzoneCenter: 8,
  triggerRightDeadzoneSide: 245,
  joystickCircleLimit: 230,
  stickTurn: 128,
  leftStickDeadzoneCenter: 18,
  leftStickDeadzoneSide: 235,
  rightStickDeadzoneCenter: 16,
  rightStickDeadzoneSide: 238,
  sensorMode: 0,
  sensorDir: 0,
  sensorRightKey0: 0,
  sensorRightKey1: 0,
  sensorMin: 12,
  sensorRightKeyBit: 0,
  sensorSwitch: 0,
  turboSpeedIdx: 2,
  turboKey: 0,
};

export const mockState: StudioState = {
  app: { name: "ArmorX Studio", version: "0.6.0-alpha.1", platform: "Windows", projectUrl: "#" },
  connection: {
    connected: true,
    headline: "Connected",
    detail: "ZJ-XT · firmware 2741",
    bluetooth: "Bluetooth ready",
    model: "ZJ-XT",
    firmware: "2741",
    battery: 87,
    discovered: [{ name: "ARMOR-X Pro", rssi: -52, source: "preview", lastSeen: new Date().toISOString() }],
  },
  busy: { active: false, text: "" },
  config: {
    crc: "0x2C40",
    crcValid: true,
    pending: [],
    fields: { ...zeroFields },
    baseline: { ...zeroFields },
    curves: {
      left: [1, 128, 65, 48, 190, 220],
      right: [0, 110, 72, 58, 182, 215],
      gyro0: [0, 64, 96, 128, 192, 255],
      gyro1: [0, 55, 90, 140, 200, 255],
      gyro2: [0, 70, 110, 150, 205, 255],
    },
    mappings: { m1: 1, m2: 0, m3: 3, m4: 4 },
    mappingTargets: [
      { id: 0, name: "A" }, { id: 1, name: "B" }, { id: 3, name: "X" }, { id: 4, name: "Y" },
      { id: 6, name: "LB" }, { id: 7, name: "RB" }, { id: 8, name: "LT" }, { id: 9, name: "RT" },
      { id: 10, name: "View" }, { id: 11, name: "Menu" }, { id: 12, name: "Guide / Xbox" },
      { id: 13, name: "L3" }, { id: 14, name: "R3" }, { id: 16, name: "D-pad Up" },
      { id: 17, name: "D-pad Down" }, { id: 18, name: "D-pad Left" }, { id: 19, name: "D-pad Right" },
    ],
  },
  profiles: [
    { name: "FPS - Fast", savedUtc: new Date().toISOString(), model: "ZJ-XT", firmware: "2741" },
    { name: "Racing", savedUtc: new Date(Date.now() - 86400000).toISOString(), model: "ZJ-XT", firmware: "2741" },
  ],
  activeProfile: "FPS - Fast",
  lastBackup: "preview-pre-write.json",
  diagnostics: ["12:01:12  Preview mode active.", "12:01:15  Config CRC valid."],
};

export const emptyGamepad: GamepadSnapshot = {
  connected: false,
  name: "No Xbox-compatible controller",
  leftX: 0,
  leftY: 0,
  rightX: 0,
  rightY: 0,
  leftTrigger: 0,
  rightTrigger: 0,
  buttons: {},
  timestamp: 0,
};

export const mockGamepad: GamepadSnapshot = {
  connected: true,
  name: "ArmorX preview controller",
  leftX: 0.34,
  leftY: 0.62,
  rightX: -0.28,
  rightY: -0.37,
  leftTrigger: 0.58,
  rightTrigger: 0.84,
  buttons: {
    A: true, B: false, X: false, Y: false,
    LB: false, RB: true, L3: true, R3: false,
    View: false, Menu: false,
    DUp: false, DDown: false, DLeft: true, DRight: false,
    P1: false, P2: false, P3: false, P4: false,
  },
  timestamp: 1,
};

async function mockInvoke(action: string, payload: Record<string, unknown>) {
  await new Promise((resolve) => setTimeout(resolve, 80));
  if (action === "state") return mockState;
  if (action === "patchConfig" && mockState.config) {
    const field = String(payload.field || "");
    const value = Number(payload.value || 0);
    if (field in mockState.config.fields) {
      (mockState.config.fields as unknown as Record<string, number>)[field] = value;
    }
    return { ok: true };
  }
  if (action === "prepareApply") {
    return { noChange: true, summary: "Preview mode: no live device write." };
  }
  if (action === "openTextFile") return { cancelled: true };
  if (action === "saveTextFile") return { cancelled: false, name: payload.name || "armorx.json" };
  return { ok: true };
}
