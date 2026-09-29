export type HelpSpec = {
  title: string;
  text: string;
  recommended: string;
};

export const help: Record<string, HelpSpec> = {
  circleLimit: {
    title: "Stick circle limit",
    text: "Recovered raw controller byte controlling the stick's outer response limit.",
    recommended: "Start from the controller baseline. Increase/decrease gradually; exact vendor percentage scaling is not proven.",
  },
  stickTurn: {
    title: "Stick turn",
    text: "Recovered raw controller byte associated with stick turn/response behavior.",
    recommended: "Keep the device baseline unless you are intentionally tuning response.",
  },
  stickDeadzone: {
    title: "Stick deadzone",
    text: "Center and side are recovered raw bytes. The visual ring is a byte-space guide, not a calibrated travel percentage.",
    recommended: "Use the loaded baseline first. Small center changes are easier to evaluate in Button Test.",
  },
  triggerDeadzone: {
    title: "Trigger deadzone",
    text: "Raw 0–255 bytes controlling the recovered trigger center/side fields.",
    recommended: "Keep the loaded baseline, then verify LT/RT live values in Button Test after tuning.",
  },
  curve: {
    title: "Response curve bytes",
    text: "Six recovered raw bytes. The graph is a control-point preview and does not claim exact firmware transfer math.",
    recommended: "Preserve the baseline unless you are testing a known curve change.",
  },
  gyro: {
    title: "Gyro / sensor",
    text: "Recovered sensor fields and curve bytes from the 144-byte configuration image.",
    recommended: "Keep the device baseline for unknown modes. Change one field at a time.",
  },
  turbo: {
    title: "Turbo speed",
    text: "Recovered turbo speed index. Exact human-friendly rate mapping is not proven for every firmware.",
    recommended: "Use the loaded baseline as the default and test behavior after a single change.",
  },
  mapping: {
    title: "Rear-button mapping",
    text: "Maps M1–M4 to live-proven public button IDs. Unknown IDs are not exposed.",
    recommended: "Choose the action you actually want; the loaded baseline is shown as the default.",
  },
  apply: {
    title: "Apply & Verify",
    text: "Reads twice, creates a full pre-write backup, writes the merged known changes, persists once, then requires two exact 144-byte read-backs.",
    recommended: "Review the exact diff before every write.",
  },
  macro: {
    title: "Macro Studio",
    text: "Builds the recovered portable V41 macro JSON format. Device macro installation is intentionally not enabled yet.",
    recommended: "Keep sequences short while testing. Maximum: 16 steps.",
  },
  buttonTest: {
    title: "Button Test",
    text: "Reads Windows' Xbox-compatible Gamepad API only. It does not send commands to the controller.",
    recommended: "Use it after remapping to confirm A/B/X/Y, L3/R3, sticks and LT/RT output.",
  },
};
