export type ConfigChange = {
  offset: number;
  before: number;
  after: number;
  label: string;
};

export type ConfigFields = {
  motorSpeedIdx: number;
  motorMax: number;
  triggerMode: number;
  triggerLeftDeadzoneCenter: number;
  triggerLeftDeadzoneSide: number;
  triggerRightDeadzoneCenter: number;
  triggerRightDeadzoneSide: number;
  joystickCircleLimit: number;
  stickTurn: number;
  leftStickDeadzoneCenter: number;
  leftStickDeadzoneSide: number;
  rightStickDeadzoneCenter: number;
  rightStickDeadzoneSide: number;
  sensorMode: number;
  sensorDir: number;
  sensorRightKey0: number;
  sensorRightKey1: number;
  sensorMin: number;
  sensorRightKeyBit: number;
  sensorSwitch: number;
  turboSpeedIdx: number;
  turboKey: number;
};

export type ConfigState = {
  crc: string;
  crcValid: boolean;
  pending: ConfigChange[];
  fields: ConfigFields;
  baseline: ConfigFields | null;
  curves: {
    left: number[];
    right: number[];
    gyro0: number[];
    gyro1: number[];
    gyro2: number[];
  };
  baselineCurves?: {
    left: number[];
    right: number[];
    gyro0: number[];
    gyro1: number[];
    gyro2: number[];
  } | null;
  mappings: { m1: number; m2: number; m3: number; m4: number };
  baselineMappings?: { m1: number; m2: number; m3: number; m4: number } | null;
  mappingTargets: { id: number; name: string }[];
};

export type ProfileRow = {
  name: string;
  savedUtc: string;
  model?: string | null;
  firmware?: string | null;
};

export type StudioState = {
  app: { name: string; version: string; platform: string; projectUrl: string };
  connection: {
    connected: boolean;
    headline: string;
    detail: string;
    bluetooth: string;
    model?: string | null;
    firmware?: string | null;
    battery?: number | null;
    discovered: { name: string; rssi?: number | null; source: string; lastSeen: string }[];
  };
  busy: { active: boolean; text: string };
  config: ConfigState | null;
  profiles: ProfileRow[];
  activeProfile?: string | null;
  lastBackup?: string | null;
  diagnostics: string[];
};

export type GamepadSnapshot = {
  connected: boolean;
  name: string;
  leftX: number;
  leftY: number;
  rightX: number;
  rightY: number;
  leftTrigger: number;
  rightTrigger: number;
  buttons: Record<string, boolean>;
  timestamp: number;
};

export type WritePlan = {
  noChange: boolean;
  token?: string;
  currentSha256?: string;
  targetSha256?: string;
  currentCrc?: string;
  targetCrc?: string;
  backup?: string;
  backupDate?: string;
  backupReason?: string;
  verification?: string;
  summary?: string;
  changes?: ConfigChange[];
};
