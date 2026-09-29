import { useEffect, useMemo, useState } from "react";
import { bridge, emptyGamepad, mockState } from "./bridge";
import { help } from "./help";
import {
  buildMacroObject,
  draftFromMacroObject,
  KEY_IDS,
  MAX_STEPS,
  type MacroDraft,
  type MacroStep,
  validateMacro,
} from "./macro";
import type { ConfigFields, GamepadSnapshot, StudioState, WritePlan } from "./types";

type Page =
  | "dashboard"
  | "sticks"
  | "triggers"
  | "gyro"
  | "mapping"
  | "profiles"
  | "macros"
  | "buttons"
  | "diagnostics"
  | "settings";

const nav: Array<{ id: Page; label: string; icon: string }> = [
  { id: "dashboard", label: "Dashboard", icon: "◈" },
  { id: "sticks", label: "Sticks", icon: "◎" },
  { id: "triggers", label: "Triggers", icon: "⌁" },
  { id: "gyro", label: "Gyro", icon: "✦" },
  { id: "mapping", label: "Mapping & Turbo", icon: "⌘" },
  { id: "profiles", label: "Profiles", icon: "▣" },
  { id: "macros", label: "Macro Studio", icon: "⚡" },
  { id: "buttons", label: "Button Test", icon: "◉" },
  { id: "diagnostics", label: "Diagnostics", icon: "≡" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

function App() {
  const [state, setState] = useState<StudioState>(mockState);
  const [gamepad, setGamepad] = useState<GamepadSnapshot>(emptyGamepad);
  const [page, setPage] = useState<Page>("dashboard");
  const [theme, setTheme] = useState<"dark" | "light">(
    (localStorage.getItem("armorx-theme") as "dark" | "light") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );
  const [about, setAbout] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<{ kind: "apply" | "restore"; data: WritePlan } | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("armorx-theme", theme);
  }, [theme]);

  useEffect(() => {
    const offState = bridge.on("state", (payload) => setState(payload as StudioState));
    const offPad = bridge.on("gamepad", (payload) => setGamepad(payload as GamepadSnapshot));
    bridge.invoke<StudioState>("state").then(setState).catch((e) => setError((e as Error).message));
    return () => { offState(); offPad(); };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  const invoke = async <T,>(action: string, payload: Record<string, unknown> = {}) => {
    try {
      setError(null);
      return await bridge.invoke<T>(action, payload);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message);
      throw e;
    }
  };

  const patch = async (field: string, value: number) => {
    await invoke("patchConfig", { field, value });
    if (!bridge.native) setState({ ...mockState });
  };

  const reviewApply = async () => {
    const result = await invoke<WritePlan>("prepareApply");
    if (result.noChange) {
      setToast(result.summary || "Nothing to write.");
      return;
    }
    setPlan({ kind: "apply", data: result });
  };

  const reviewRestore = async () => {
    const result = await invoke<WritePlan>("prepareRestore");
    if (result.noChange) {
      setToast(result.summary || "Backup already matches.");
      return;
    }
    setPlan({ kind: "restore", data: result });
  };

  const commitPlan = async () => {
    if (!plan?.data.token) return;
    const action = plan.kind === "apply" ? "commitApply" : "commitRestore";
    const result = await invoke<{ status: string; crc?: string }>(action, { token: plan.data.token });
    setPlan(null);
    setToast(`${result.status} · ${result.crc || "verified"}`);
  };

  const content = (() => {
    switch (page) {
      case "dashboard": return <Dashboard state={state} gamepad={gamepad} invoke={invoke} navigate={setPage} />;
      case "sticks": return <Sticks state={state} patch={patch} />;
      case "triggers": return <Triggers state={state} patch={patch} gamepad={gamepad} />;
      case "gyro": return <Gyro state={state} patch={patch} />;
      case "mapping": return <Mapping state={state} patch={patch} />;
      case "profiles": return <Profiles state={state} invoke={invoke} />;
      case "macros": return <MacroStudio invoke={invoke} />;
      case "buttons": return <ButtonTest gamepad={gamepad} />;
      case "diagnostics": return <Diagnostics state={state} invoke={invoke} />;
      case "settings": return <Settings state={state} theme={theme} setTheme={setTheme} invoke={invoke} />;
    }
  })();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark"><span>A</span><i>X</i></div>
          <div className="brandWords"><b>ArmorX</b><small>STUDIO</small></div>
        </div>
        <nav>
          {nav.map((item) => (
            <button key={item.id} className={page === item.id ? "active" : ""} onClick={() => setPage(item.id)}>
              <span className="navIcon">{item.icon}</span><span className="navLabel">{item.label}</span>
              {item.id === "buttons" && gamepad.connected && <i className="liveDot" />}
            </button>
          ))}
        </nav>
        <div className="sidebarBottom">
          <div className="miniDevice">
            <span className={`statusOrb ${state.connection.connected ? "online" : ""}`} />
            <div><b>{state.connection.connected ? state.connection.model || "ARMOR-X" : "Disconnected"}</b>
            <small>{state.connection.connected ? `${state.connection.battery ?? "—"}% battery` : "BLE waiting"}</small></div>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{nav.find((n) => n.id === page)?.label}</h1>
            <p>{state.busy.active ? state.busy.text : state.connection.detail}</p>
          </div>
          <div className="topActions">
            <button className="iconButton" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} title="Toggle theme">
              {theme === "dark" ? "☀" : "☾"}
            </button>
            <button className="ghostButton" onClick={() => setAbout(true)}>About</button>
            <button className={`connectPill ${state.connection.connected ? "connected" : ""}`}
              disabled={state.busy.active}
              onClick={() => invoke(state.connection.connected ? "disconnect" : "connect")}>
              <span />{state.connection.connected ? "Connected" : "Connect"}
            </button>
          </div>
        </header>

        {state.busy.active && <div className="busyBar"><i /></div>}
        <section className="content">{content}</section>

        {state.config && (
          <div className="applyDock">
            <div className="dockState">
              <span className={state.config.pending.length ? "pendingDot" : "cleanDot"} />
              <div>
                <b>{state.config.pending.length ? `${state.config.pending.length} pending change${state.config.pending.length === 1 ? "" : "s"}` : "Configuration clean"}</b>
                <small>CRC {state.config.crc} · unknown bytes preserved</small>
              </div>
              <HelpTip spec={help.apply} baseline="Automatic verified backup" />
            </div>
            <div className="dockButtons">
              <button className="secondary" onClick={reviewRestore} disabled={!state.connection.connected || state.busy.active}>Restore backup</button>
              <button className="primary" onClick={reviewApply} disabled={!state.connection.connected || !state.config.pending.length || state.busy.active}>
                Review & Apply
              </button>
            </div>
          </div>
        )}
      </main>

      {plan && <WritePlanModal plan={plan} onCancel={() => setPlan(null)} onConfirm={commitPlan} />}
      {about && <About state={state} invoke={invoke} onClose={() => setAbout(false)} />}
      {error && <div className="toast error"><b>Action stopped</b><span>{error}</span><button onClick={() => setError(null)}>×</button></div>}
      {toast && <div className="toast success"><b>Done</b><span>{toast}</span></div>}
    </div>
  );
}

function Dashboard({ state, gamepad, invoke, navigate }: {
  state: StudioState;
  gamepad: GamepadSnapshot;
  invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T>;
  navigate: (p: Page) => void;
}) {
  return (
    <div className="pageStack">
      <div className="heroGrid">
        <div className="heroCard">
          <div className="eyebrow">ARMOR-X PRO</div>
          <h2>{state.connection.connected ? "Controller ready." : "One click from ready."}</h2>
          <p>{state.connection.connected
            ? "Your configuration is loaded locally. Review exact changes before any write."
            : "Power on the adapter, keep the mobile app disconnected, then let ArmorX Studio recover the remembered device."}</p>
          <div className="heroActions">
            <button className="primary big" onClick={() => invoke(state.connection.connected ? "readConfig" : "connect")}>
              {state.connection.connected ? "Refresh configuration" : "Connect / Recover"}
            </button>
            <button className="secondary big" onClick={() => navigate("buttons")}>Open Button Test</button>
          </div>
          <div className="safetyStrip"><span>✓</span><b>Safe write path</b><small>2× read · full backup · exact diff · 2× verify</small></div>
        </div>
        <ControllerMini gamepad={gamepad} />
      </div>

      <div className="statGrid">
        <Stat label="Battery" value={state.connection.battery == null ? "—" : `${state.connection.battery}%`} accent="mint" sub="BLE reported" />
        <Stat label="Firmware" value={state.connection.firmware || "—"} sub={state.connection.model || "No device"} />
        <Stat label="Profile" value={state.activeProfile || "Live"} sub="Tray synchronized" />
        <Stat label="Pending" value={String(state.config?.pending.length || 0)} accent={state.config?.pending.length ? "amber" : "mint"} sub="Known editable bytes" />
      </div>

      <div className="twoCol">
        <Card title="Quick destinations" subtitle="Everything important within one click.">
          <div className="quickGrid">
            {[
              ["sticks", "◎", "Stick Lab", "Deadzones, response curves, circle limit"],
              ["triggers", "⌁", "Trigger Lab", "LT / RT tuning with live input"],
              ["mapping", "⌘", "Rear Mapping", "M1–M4 and turbo settings"],
              ["macros", "⚡", "Macro Studio", "Drag, stack and export 16-step macros"],
            ].map(([id, icon, title, text]) => (
              <button className="quickCard" key={id} onClick={() => navigate(id as Page)}>
                <span>{icon}</span><div><b>{title}</b><small>{text}</small></div><i>›</i>
              </button>
            ))}
          </div>
        </Card>
        <Card title="Connection" subtitle={state.connection.bluetooth}>
          <div className="connectionDetail">
            <div className={`signalOrb ${state.connection.connected ? "online" : ""}`}><span /></div>
            <div>
              <h3>{state.connection.headline}</h3>
              <p>{state.connection.detail}</p>
            </div>
          </div>
          <div className="deviceRows">
            <Row label="Model" value={state.connection.model || "—"} />
            <Row label="Firmware" value={state.connection.firmware || "—"} />
            <Row label="Config CRC" value={state.config?.crc || "—"} />
            <Row label="Backup" value={state.lastBackup || "Not created this session"} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function Sticks({ state, patch }: { state: StudioState; patch: (f: string, v: number) => Promise<void> }) {
  const cfg = state.config;
  if (!cfg) return <EmptyConfig />;
  return (
    <div className="pageStack">
      <InfoBanner title="Visuals are intentionally honest">
        The graphs use recovered raw 0–255 configuration bytes. They are excellent for comparing edits, but are not labeled as physical percentages until the firmware scaling is proven.
      </InfoBanner>
      <div className="twoCol">
        <StickCard side="Left" fields={cfg.fields} baseline={cfg.baseline} curve={cfg.curves.left} baselineCurve={cfg.baselineCurves?.left} prefix="leftCurve." patch={patch}
          centerKey="leftStickDeadzoneCenter" sideKey="leftStickDeadzoneSide" />
        <StickCard side="Right" fields={cfg.fields} baseline={cfg.baseline} curve={cfg.curves.right} baselineCurve={cfg.baselineCurves?.right} prefix="rightCurve." patch={patch}
          centerKey="rightStickDeadzoneCenter" sideKey="rightStickDeadzoneSide" />
      </div>
      <Card title="Global stick behavior" subtitle="Recovered common stick fields.">
        <div className="controlGrid">
          <SliderControl label="Circle limit" field="joystickCircleLimit" value={cfg.fields.joystickCircleLimit} baseline={cfg.baseline?.joystickCircleLimit} patch={patch} spec={help.circleLimit} />
          <SliderControl label="Stick turn" field="stickTurn" value={cfg.fields.stickTurn} baseline={cfg.baseline?.stickTurn} patch={patch} spec={help.stickTurn} />
        </div>
      </Card>
    </div>
  );
}

function StickCard({ side, fields, baseline, curve, baselineCurve, prefix, patch, centerKey, sideKey }: {
  side: string; fields: ConfigFields; baseline: ConfigFields | null; curve: number[]; baselineCurve?: number[]; prefix: string;
  patch: (f: string, v: number) => Promise<void>; centerKey: keyof ConfigFields; sideKey: keyof ConfigFields;
}) {
  return (
    <Card title={`${side} stick`} subtitle="Deadzone + six recovered curve bytes" className="stickCard">
      <div className="stickVisualRow">
        <StickByteVisual center={Number(fields[centerKey])} side={Number(fields[sideKey])} label={side} />
        <CurvePlot values={curve} />
      </div>
      <SliderControl label="Center deadzone" field={String(centerKey)} value={Number(fields[centerKey])} baseline={baseline ? Number(baseline[centerKey]) : undefined} patch={patch} spec={help.stickDeadzone} />
      <SliderControl label="Side deadzone" field={String(sideKey)} value={Number(fields[sideKey])} baseline={baseline ? Number(baseline[sideKey]) : undefined} patch={patch} spec={help.stickDeadzone} />
      <div className="curveControls">
        {curve.map((value, index) => (
          <SliderControl key={index} compact label={["Mode", "YDivx", "P1 X", "P1 Y", "P2 X", "P2 Y"][index]}
            field={`${prefix}${index}`} value={value} baseline={baselineCurve?.[index]} patch={patch} spec={help.curve} />
        ))}
      </div>
    </Card>
  );
}

function Triggers({ state, patch, gamepad }: { state: StudioState; patch: (f: string, v: number) => Promise<void>; gamepad: GamepadSnapshot }) {
  const cfg = state.config;
  if (!cfg) return <EmptyConfig />;
  return (
    <div className="pageStack">
      <div className="triggerHero">
        <TriggerTower label="LT" value={gamepad.leftTrigger} live />
        <div className="triggerCopy">
          <div className="eyebrow">TRIGGER LAB</div>
          <h2>Feel the response before you save it.</h2>
          <p>Keep Button Test open after applying to validate the real Windows output. Live LT/RT pressure is visualized here whenever the Xbox-compatible device is present.</p>
          <div className="triggerMode">Trigger mode byte <strong>{cfg.fields.triggerMode}</strong><HelpTip spec={help.triggerDeadzone} baseline={String(cfg.baseline?.triggerMode ?? "—")} /></div>
        </div>
        <TriggerTower label="RT" value={gamepad.rightTrigger} live />
      </div>
      <Card title="Trigger mode" subtitle="Recovered raw mode byte — keep the loaded default unless you know the intended mode.">
        <SliderControl label="Trigger mode byte" field="triggerMode" value={cfg.fields.triggerMode} baseline={cfg.baseline?.triggerMode} patch={patch} spec={help.triggerDeadzone} />
      </Card>
      <div className="twoCol">
        <Card title="Left trigger" subtitle="Recovered LT deadzone bytes.">
          <SliderControl label="Center deadzone" field="triggerLeftDeadzoneCenter" value={cfg.fields.triggerLeftDeadzoneCenter} baseline={cfg.baseline?.triggerLeftDeadzoneCenter} patch={patch} spec={help.triggerDeadzone} />
          <SliderControl label="Side deadzone" field="triggerLeftDeadzoneSide" value={cfg.fields.triggerLeftDeadzoneSide} baseline={cfg.baseline?.triggerLeftDeadzoneSide} patch={patch} spec={help.triggerDeadzone} />
        </Card>
        <Card title="Right trigger" subtitle="Recovered RT deadzone bytes.">
          <SliderControl label="Center deadzone" field="triggerRightDeadzoneCenter" value={cfg.fields.triggerRightDeadzoneCenter} baseline={cfg.baseline?.triggerRightDeadzoneCenter} patch={patch} spec={help.triggerDeadzone} />
          <SliderControl label="Side deadzone" field="triggerRightDeadzoneSide" value={cfg.fields.triggerRightDeadzoneSide} baseline={cfg.baseline?.triggerRightDeadzoneSide} patch={patch} spec={help.triggerDeadzone} />
        </Card>
      </div>
    </div>
  );
}

function Gyro({ state, patch }: { state: StudioState; patch: (f: string, v: number) => Promise<void> }) {
  const cfg = state.config;
  if (!cfg) return <EmptyConfig />;
  return (
    <div className="pageStack">
      <InfoBanner title="Sensor controls are raw recovered fields">
        ArmorX Studio never invents labels for unknown modes. Hover the question marks to see what is proven and what should stay at the device baseline.
      </InfoBanner>
      <Card title="Gyro / sensor core" subtitle="Known byte locations from the 144-byte image.">
        <div className="controlGrid">
          {(["sensorMode", "sensorDir", "sensorRightKey0", "sensorRightKey1", "sensorMin"] as Array<keyof ConfigFields>).map((field) => (
            <SliderControl key={field} label={humanize(field)} field={field} value={Number(cfg.fields[field])}
              baseline={cfg.baseline ? Number(cfg.baseline[field]) : undefined} patch={patch} spec={help.gyro} />
          ))}
        </div>
      </Card>
      <div className="threeCol">
        {[cfg.curves.gyro0, cfg.curves.gyro1, cfg.curves.gyro2].map((curve, gi) => (
          <Card key={gi} title={`Gyro curve ${gi + 1}`} subtitle="Recovered six-byte curve">
            <CurvePlot values={curve} />
            {curve.map((value, i) => (
              <SliderControl key={i} compact label={`Byte ${i + 1}`} field={`gyro${gi}.${i}`} value={value}
                baseline={[cfg.baselineCurves?.gyro0, cfg.baselineCurves?.gyro1, cfg.baselineCurves?.gyro2][gi]?.[i]}
                patch={patch} spec={help.curve} />
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}

function Mapping({ state, patch }: { state: StudioState; patch: (f: string, v: number) => Promise<void> }) {
  const cfg = state.config;
  if (!cfg) return <EmptyConfig />;
  return (
    <div className="pageStack">
      <div className="mappingGrid">
        {(["m1", "m2", "m3", "m4"] as const).map((key, index) => {
          const field = `${key}TargetId`;
          const current = cfg.mappings[key];
          const baselineId = cfg.baselineMappings?.[key];
          const baselineName = baselineId == null
            ? "Loaded device mapping"
            : cfg.mappingTargets.find((target) => target.id === baselineId)?.name || String(baselineId);
          return (
            <div className={`mappingCard m${index + 1}`} key={key}>
              <div className="mappingBadge">{key.toUpperCase()}</div>
              <div><h3>Rear button {index + 1}</h3><p>Map to a proven public input ID.</p></div>
              <HelpTip spec={help.mapping} baseline={baselineName} />
              <select value={current} onChange={(e) => patch(field, Number(e.target.value))}>
                {cfg.mappingTargets.map((target) => <option key={target.id} value={target.id}>{target.name} · {target.id}</option>)}
              </select>
            </div>
          );
        })}
      </div>
      <Card title="Turbo" subtitle="Recovered turbo controls">
        <div className="controlGrid">
          <SliderControl label="Turbo speed index" field="turboSpeedIdx" value={cfg.fields.turboSpeedIdx} baseline={cfg.baseline?.turboSpeedIdx} patch={patch} spec={help.turbo} />
          <SliderControl label="Motor speed index" field="motorSpeedIdx" value={cfg.fields.motorSpeedIdx} baseline={cfg.baseline?.motorSpeedIdx} patch={patch} spec={help.turbo} />
          <SliderControl label="Motor maximum" field="motorMax" value={cfg.fields.motorMax} baseline={cfg.baseline?.motorMax} patch={patch} spec={help.turbo} />
        </div>
      </Card>
    </div>
  );
}

function Profiles({ state, invoke }: { state: StudioState; invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T> }) {
  const [name, setName] = useState("");
  const action = async (a: string, payload: Record<string, unknown> = {}) => { await invoke(a, payload); };
  return (
    <div className="pageStack">
      <div className="profilesHero">
        <div><div className="eyebrow">LOCAL LIBRARY</div><h2>Profiles that stay yours.</h2><p>Stored under Local AppData. Loading a profile only changes the editor; the controller is untouched until Review & Apply.</p></div>
        <div className="profileSaveBox"><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Profile name" />
          <button className="primary" disabled={!state.config || !name.trim()} onClick={() => action("saveProfile", { name }).then(() => setName(""))}>Save current</button></div>
      </div>
      <div className="profileGrid">
        {state.profiles.map((profile) => (
          <div className={`profileCard ${state.activeProfile === profile.name ? "active" : ""}`} key={profile.name}>
            <div className="profileIcon">◫</div>
            <div className="profileMeta"><h3>{profile.name}</h3><p>{profile.model || "ArmorX"} · FW {profile.firmware || "—"}</p><small>{new Date(profile.savedUtc).toLocaleString()}</small></div>
            <div className="profileActions">
              <button onClick={() => action("loadProfile", { name: profile.name })}>Load</button>
              <button onClick={() => action("exportProfile", { name: profile.name })}>Export</button>
              <button className="dangerText" onClick={() => action("deleteProfile", { name: profile.name })}>Delete</button>
            </div>
          </div>
        ))}
        {!state.profiles.length && <div className="emptyCard">No local profiles yet.</div>}
      </div>
      <div className="rowActions">
        <button className="secondary" onClick={() => action("importProfile")}>Import profile</button>
        <button className="secondary" onClick={() => action("openProfilesFolder")}>Open profiles folder</button>
      </div>
    </div>
  );
}

function MacroStudio({ invoke }: { invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T> }) {
  const [draft, setDraft] = useState<MacroDraft>({
    name: "My Combo",
    trigger: "M1",
    mode: "tap",
    repeatTime: 200,
    active: false,
    steps: [
      { id: crypto.randomUUID(), keys: "A", duration: 80, interval: 50 },
      { id: crypto.randomUUID(), keys: "B+RT", duration: 120, interval: 70 },
    ],
  });
  const [selected, setSelected] = useState(0);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const errors = useMemo(() => validateMacro(draft), [draft]);

  const updateStep = (index: number, patch: Partial<MacroStep>) =>
    setDraft((current) => ({ ...current, steps: current.steps.map((s, i) => i === index ? { ...s, ...patch } : s) }));

  const addStep = () => {
    if (draft.steps.length >= MAX_STEPS) return;
    setDraft((current) => ({ ...current, steps: [...current.steps, { id: crypto.randomUUID(), keys: "A", duration: 100, interval: 50 }] }));
    setSelected(draft.steps.length);
  };

  const removeStep = (index: number) => {
    if (draft.steps.length <= 1) return;
    setDraft((current) => ({ ...current, steps: current.steps.filter((_, i) => i !== index) }));
    setSelected(Math.max(0, selected - (index <= selected ? 1 : 0)));
  };

  const drop = (target: number) => {
    if (dragIndex == null || dragIndex === target) return setDragIndex(null);
    const next = [...draft.steps];
    const [item] = next.splice(dragIndex, 1);
    next.splice(target, 0, item);
    setDraft({ ...draft, steps: next });
    setSelected(target);
    setDragIndex(null);
  };

  const addKey = (key: string) => {
    const step = draft.steps[selected];
    const parts = step.keys.split("+").filter(Boolean);
    if (!parts.includes(key)) updateStep(selected, { keys: [...parts, key].join("+") });
  };

  const exportMacro = async () => {
    const obj = buildMacroObject(draft);
    await invoke("saveTextFile", {
      title: "Export ArmorX macro",
      name: `${draft.name.replace(/[^a-z0-9_-]+/gi, "-") || "armorx-macro"}.json`,
      text: JSON.stringify(obj, null, 2),
    });
  };

  const importMacro = async () => {
    const file = await invoke<{ cancelled: boolean; text?: string }>("openTextFile", { title: "Open ArmorX macro" });
    if (!file.cancelled && file.text) setDraft(draftFromMacroObject(JSON.parse(file.text)));
  };

  return (
    <div className="macroStudio">
      <div className="macroHeader">
        <div><div className="eyebrow">MACRO STUDIO <HelpTip spec={help.macro} /></div><h2>Build combos like a timeline.</h2>
          <p>Drag cards to reorder. Tap keys to add chords. Export portable V41 JSON when the sequence feels right.</p></div>
        <div className="macroHeaderActions"><button className="secondary" onClick={importMacro}>Import</button><button className="primary" disabled={errors.length > 0} onClick={exportMacro}>Export macro</button></div>
      </div>

      <div className="macroMeta">
        <label>Name<input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></label>
        <label>Rear trigger<select value={draft.trigger} onChange={(e) => setDraft({ ...draft, trigger: e.target.value as MacroDraft["trigger"] })}>
          {Object.keys({ M1: 1, M2: 1, M3: 1, M4: 1 }).map((k) => <option key={k}>{k}</option>)}
        </select></label>
        <label>Mode<select value={draft.mode} onChange={(e) => setDraft({ ...draft, mode: e.target.value as MacroDraft["mode"] })}>
          <option value="tap">Tap</option><option value="long_press">Long press</option><option value="tap_cycle">Tap cycle</option><option value="long_press_cycle">Long-press cycle</option>
        </select></label>
        <label>Repeat<input type="number" min={0} value={draft.repeatTime} onChange={(e) => setDraft({ ...draft, repeatTime: Number(e.target.value) })} /><span>ms</span></label>
      </div>

      <div className="keyPalette">
        <span>KEY PALETTE</span>
        {Object.keys(KEY_IDS).filter((key) => !key.includes("_") && !["M1", "M2", "M3", "M4"].includes(key)).map((key) =>
          <button key={key} onClick={() => addKey(key)}>{key}</button>)}
      </div>

      <div className="macroTimeline">
        {draft.steps.map((step, index) => (
          <div key={step.id} className={`macroStep ${selected === index ? "selected" : ""} ${dragIndex === index ? "dragging" : ""}`}
            draggable
            onDragStart={() => setDragIndex(index)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => drop(index)}
            onClick={() => setSelected(index)}>
            <div className="dragHandle">⋮⋮</div>
            <div className="stepIndex">{String(index + 1).padStart(2, "0")}</div>
            <div className="stepMain"><input value={step.keys} onChange={(e) => updateStep(index, { keys: e.target.value.toUpperCase() })} />
              <div className="stepTiming"><label>HOLD <input type="number" min={0} value={step.duration} onChange={(e) => updateStep(index, { duration: Number(e.target.value) })} /> ms</label>
              <label>GAP <input type="number" min={0} value={step.interval} onChange={(e) => updateStep(index, { interval: Number(e.target.value) })} /> ms</label></div></div>
            <button className="removeStep" onClick={(e) => { e.stopPropagation(); removeStep(index); }}>×</button>
            {index < draft.steps.length - 1 && <div className="timelineLink"><i /></div>}
          </div>
        ))}
        <button className="addStep" onClick={addStep} disabled={draft.steps.length >= MAX_STEPS}><span>＋</span>Add another beat <small>{draft.steps.length}/{MAX_STEPS}</small></button>
      </div>
      <div className={`macroValidation ${errors.length ? "bad" : "good"}`}>
        <span>{errors.length ? "!" : "✓"}</span>
        <div><b>{errors.length ? "Needs attention" : "Portable macro is valid"}</b>
          <small>{errors.length ? errors.join(" · ") : "Offline only — no device macro write will occur in this release."}</small></div>
      </div>
    </div>
  );
}

function ButtonTest({ gamepad }: { gamepad: GamepadSnapshot }) {
  return (
    <div className="pageStack">
      <InfoBanner title="Live Windows input — read only">
        This page reads the Windows Xbox-compatible Gamepad API. It never sends BLE or USB commands. L3/R3, stick motion and LT/RT pressure are highlighted in real time. <HelpTip spec={help.buttonTest} />
      </InfoBanner>
      <div className="testerCard">
        <div className="testerTop">
          <div><div className="eyebrow">LIVE INPUT</div><h2>{gamepad.connected ? "Controller detected" : "Waiting for controller…"}</h2>
            <p>{gamepad.name}</p></div>
          <div className={`liveBadge ${gamepad.connected ? "on" : ""}`}><i />{gamepad.connected ? "LIVE · 30 FPS" : "NO INPUT"}</div>
        </div>
        <ControllerTester gamepad={gamepad} />
        <div className="analogReadouts">
          <Analog label="LEFT STICK" x={gamepad.leftX} y={gamepad.leftY} pressed={gamepad.buttons.L3} />
          <Analog label="RIGHT STICK" x={gamepad.rightX} y={gamepad.rightY} pressed={gamepad.buttons.R3} />
          <div className="triggerReadout"><b>LT</b><div><i style={{ width: `${gamepad.leftTrigger * 100}%` }} /></div><strong>{Math.round(gamepad.leftTrigger * 100)}%</strong></div>
          <div className="triggerReadout"><b>RT</b><div><i style={{ width: `${gamepad.rightTrigger * 100}%` }} /></div><strong>{Math.round(gamepad.rightTrigger * 100)}%</strong></div>
        </div>
      </div>
    </div>
  );
}

function ControllerTester({ gamepad }: { gamepad: GamepadSnapshot }) {
  const b = (name: string) => gamepad.buttons[name] || false;
  const stick = (x: number, y: number) => `translate(${x * 16}px, ${-y * 16}px)`;
  return (
    <div className="controllerStage">
      <div className="controllerGlow" />
      <svg className="controllerSvg" viewBox="0 0 760 430" role="img" aria-label="Live controller visualization">
        <defs>
          <linearGradient id="bodyGrad" x1="0" x2="1"><stop offset="0" stopColor="var(--controller-a)" /><stop offset="0.5" stopColor="var(--controller-b)" /><stop offset="1" stopColor="var(--controller-a)" /></linearGradient>
          <filter id="glow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        <path className="padBody" d="M155 90 C220 42 300 54 380 84 C460 54 540 42 605 90 C667 137 684 247 649 329 C629 377 590 395 563 363 L493 283 C465 252 432 243 380 244 C328 243 295 252 267 283 L197 363 C170 395 131 377 111 329 C76 247 93 137 155 90Z" />
        <rect className={`shoulder ${b("LB") ? "pressed" : ""}`} x="155" y="67" rx="13" width="122" height="24" />
        <rect className={`shoulder ${b("RB") ? "pressed" : ""}`} x="483" y="67" rx="13" width="122" height="24" />
        <TriggerSvg x={195} label="LT" value={gamepad.leftTrigger} />
        <TriggerSvg x={515} label="RT" value={gamepad.rightTrigger} />

        <g className={`stickSvg ${b("L3") ? "pressed" : ""}`} style={{ transform: stick(gamepad.leftX, gamepad.leftY), transformOrigin: "260px 205px" }}>
          <circle cx="260" cy="205" r="51" className="stickOuter" /><circle cx="260" cy="205" r="35" className="stickInner" />
          <text x="260" y="210" textAnchor="middle">L3</text>
        </g>
        <g className={`stickSvg ${b("R3") ? "pressed" : ""}`} style={{ transform: stick(gamepad.rightX, gamepad.rightY), transformOrigin: "475px 284px" }}>
          <circle cx="475" cy="284" r="51" className="stickOuter" /><circle cx="475" cy="284" r="35" className="stickInner" />
          <text x="475" y="289" textAnchor="middle">R3</text>
        </g>

        <g className="dpad">
          <rect className={b("DUp") ? "pressed" : ""} x="173" y="246" width="40" height="58" rx="8" />
          <rect className={b("DDown") ? "pressed" : ""} x="173" y="322" width="40" height="58" rx="8" />
          <rect className={b("DLeft") ? "pressed" : ""} x="135" y="284" width="58" height="40" rx="8" />
          <rect className={b("DRight") ? "pressed" : ""} x="193" y="284" width="58" height="40" rx="8" />
        </g>

        <FaceButton x={575} y={191} label="Y" pressed={b("Y")} className="yellow" />
        <FaceButton x={623} y={239} label="B" pressed={b("B")} className="red" />
        <FaceButton x={527} y={239} label="X" pressed={b("X")} className="blue" />
        <FaceButton x={575} y={287} label="A" pressed={b("A")} className="green" />

        <circle className={`systemButton ${b("View") ? "pressed" : ""}`} cx="339" cy="183" r="18" />
        <circle className={`systemButton ${b("Menu") ? "pressed" : ""}`} cx="421" cy="183" r="18" />
        <text x="339" y="188" textAnchor="middle" className="sysText">≡</text>
        <text x="421" y="188" textAnchor="middle" className="sysText">⋯</text>
      </svg>
      <div className={`l3Callout ${b("L3") ? "hot" : ""}`}><span>L3</span><small>{b("L3") ? "CLICKED" : "stick click"}</small></div>
      <div className={`r3Callout ${b("R3") ? "hot" : ""}`}><span>R3</span><small>{b("R3") ? "CLICKED" : "stick click"}</small></div>
    </div>
  );
}

function TriggerSvg({ x, label, value }: { x: number; label: string; value: number }) {
  return <g className="triggerSvg"><rect x={x} y="28" width="50" height="74" rx="19" className="triggerShell" />
    <rect x={x + 4} y={98 - value * 66} width="42" height={value * 66} rx="15" className="triggerFill" filter={value > .05 ? "url(#glow)" : undefined} />
    <text x={x + 25} y="20" textAnchor="middle">{label}</text></g>;
}

function FaceButton({ x, y, label, pressed, className }: { x: number; y: number; label: string; pressed: boolean; className: string }) {
  return <g className={`face ${className} ${pressed ? "pressed" : ""}`}><circle cx={x} cy={y} r="27" /><text x={x} y={y + 7} textAnchor="middle">{label}</text></g>;
}

function ControllerMini({ gamepad }: { gamepad: GamepadSnapshot }) {
  return <div className="miniControllerCard"><div className="miniAura" />
    <div className="miniPad"><span className="miniStick left" /><span className="miniStick right" /><i className="faceDot a" /><i className="faceDot b" /><i className="faceDot x" /><i className="faceDot y" /></div>
    <div className="miniCaption"><span className={gamepad.connected ? "online" : ""} />{gamepad.connected ? "Windows input active" : "Open Button Test for live input"}</div></div>;
}

function Diagnostics({ state, invoke }: { state: StudioState; invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T> }) {
  return <div className="pageStack"><Card title="Diagnostics" subtitle="End-user log; connection addresses and device UUID are not displayed here.">
    <pre className="logBox">{state.diagnostics.length ? state.diagnostics.join("\n") : "No diagnostics yet."}</pre>
    <div className="rowActions"><button className="primary" onClick={() => invoke("exportDiagnostics")}>Export diagnostics</button><button className="secondary" onClick={() => invoke("openBackupsFolder")}>Open backups</button></div>
  </Card></div>;
}

function Settings({ state, theme, setTheme, invoke }: {
  state: StudioState; theme: "dark" | "light"; setTheme: (v: "dark" | "light") => void;
  invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T>;
}) {
  return <div className="pageStack">
    <Card title="Appearance" subtitle="Stored locally in the UI.">
      <div className="settingRow"><div><b>Theme</b><small>Switch instantly without restarting ArmorX Studio.</small></div>
        <div className="segmented"><button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}>Dark</button><button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}>Light</button></div></div>
    </Card>
    <Card title="System tray" subtitle="Essential status stays visible when the window is hidden.">
      <div className="settingRow"><div><b>Tray summary</b><small>Connection · battery · active profile</small></div><span className="settingValue">{state.connection.battery ?? "—"}% · {state.activeProfile || "Live"}</span></div>
      <div className="rowActions"><button className="secondary" onClick={() => invoke("minimizeToTray")}>Minimize to tray now</button></div>
    </Card>
    <Card title="Safety defaults" subtitle="These are intentionally not optional in the normal GUI.">
      <div className="safetyList"><span>✓ Two agreeing reads before write review</span><span>✓ Full pre-write backup</span><span>✓ Only known editable bytes merged</span><span>✓ Two exact 144-byte read-backs</span><span>✓ No blind retry after a partial write</span></div>
    </Card>
  </div>;
}

function WritePlanModal({ plan, onCancel, onConfirm }: { plan: { kind: "apply" | "restore"; data: WritePlan }; onCancel: () => void; onConfirm: () => void }) {
  const d = plan.data;
  return <Modal onClose={onCancel}><div className="modalIcon warning">!</div><div className="eyebrow">{plan.kind === "apply" ? "REVIEW WRITE" : "REVIEW RESTORE"}</div>
    <h2>{plan.kind === "apply" ? "Apply these exact changes?" : "Restore this exact backup?"}</h2>
    <p className="modalLead">{d.verification}</p>
    <div className="hashGrid"><div><small>CURRENT CRC</small><b>{d.currentCrc}</b><code>{shortHash(d.currentSha256)}</code></div>
      <div><small>TARGET CRC</small><b>{d.targetCrc}</b><code>{shortHash(d.targetSha256)}</code></div></div>
    <div className="changeList">{d.changes?.map((c) => <div key={c.offset}><span>Offset {c.offset}</span><b>{c.label}</b><code>{c.before} → {c.after}</code></div>)}</div>
    {d.backup && <div className="backupNote">◫ {d.backup}</div>}
    {d.backupDate && <div className="backupNote">◫ Backup: {d.backupDate} · {d.backupReason}</div>}
    <div className="modalActions"><button className="secondary" onClick={onCancel}>Cancel</button><button className="primary dangerPrimary" onClick={onConfirm}>{plan.kind === "apply" ? "Apply & Verify" : "Restore & Verify"}</button></div>
  </Modal>;
}

function About({ state, invoke, onClose }: { state: StudioState; invoke: <T>(a: string, p?: Record<string, unknown>) => Promise<T>; onClose: () => void }) {
  return <Modal onClose={onClose}><div className="aboutMark">AX</div><h2>ArmorX Studio</h2><p className="modalLead">Community-built Windows configurator for BIGBIG WON ARMOR-X Pro. Not affiliated with BIGBIG WON.</p>
    <div className="aboutFacts"><Row label="Version" value={state.app.version} /><Row label="Backend" value=".NET 8 · Windows BLE" /><Row label="UI" value="React · WebView2" /><Row label="Write safety" value="backup + exact diff + 2× verify" /></div>
    <div className="modalActions"><button className="secondary" onClick={() => invoke("openProject")}>Project on GitHub</button><button className="primary" onClick={onClose}>Close</button></div></Modal>;
}

function Card({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return <div className={`card ${className}`}><div className="cardHead"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div></div>{children}</div>;
}
function Stat({ label, value, sub, accent = "" }: { label: string; value: string; sub: string; accent?: string }) {
  return <div className={`stat ${accent}`}><small>{label}</small><b>{value}</b><span>{sub}</span></div>;
}
function Row({ label, value }: { label: string; value: string }) { return <div className="detailRow"><span>{label}</span><b>{value}</b></div>; }

function HelpTip({ spec, baseline }: { spec: { title: string; text: string; recommended: string }; baseline?: string }) {
  return <span className="helpTip" tabIndex={0}>?<span className="helpBubble"><b>{spec.title}</b><p>{spec.text}</p><em>{spec.recommended}</em>{baseline != null && <small>Baseline / default: {baseline}</small>}</span></span>;
}

function SliderControl({ label, field, value, baseline, patch, spec, compact = false }: {
  label: string; field: string; value: number; baseline?: number; patch: (f: string, v: number) => Promise<void>;
  spec: { title: string; text: string; recommended: string }; compact?: boolean;
}) {
  return <div className={`sliderControl ${compact ? "compact" : ""}`}><div className="sliderLabel"><span>{label}<HelpTip spec={spec} baseline={baseline == null ? undefined : String(baseline)} /></span><b>{value}</b></div>
    <input type="range" min={0} max={255} value={value} onChange={(e) => patch(field, Number(e.target.value))} />
    <div className="sliderScale"><span>0</span><span>{baseline != null ? `baseline ${baseline}` : "raw byte"}</span><span>255</span></div></div>;
}

function StickByteVisual({ center, side, label }: { center: number; side: number; label: string }) {
  const c = 12 + center / 255 * 32;
  const s = 20 + side / 255 * 45;
  return <div className="stickByteVisual"><div className="byteRings"><i className="outerRing" style={{ width: s * 2, height: s * 2 }} /><i className="innerRing" style={{ width: c * 2, height: c * 2 }} /><span>{label[0]}</span></div>
    <small>center {center} · side {side}</small></div>;
}

function CurvePlot({ values }: { values: number[] }) {
  const points = [[0, 255], [values[2] || 64, 255 - (values[3] || 64)], [values[4] || 190, 255 - (values[5] || 190)], [255, 0]];
  return <div className="curvePlot"><svg viewBox="0 0 255 255" preserveAspectRatio="none"><line x1="0" y1="255" x2="255" y2="0" className="curveGuide" />
    <polyline points={points.map((p) => p.join(",")).join(" ")} className="curveLine" />{points.slice(1, 3).map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="7" className="curvePoint" />)}</svg>
    <span>raw-byte curve preview</span></div>;
}

function TriggerTower({ label, value, live }: { label: string; value: number; live?: boolean }) {
  return <div className="triggerTower"><div className="triggerCap">{label}</div><div className="triggerTrack"><i style={{ height: `${Math.max(2, value * 100)}%` }} /></div><b>{Math.round(value * 100)}%</b>{live && <small>LIVE</small>}</div>;
}

function Analog({ label, x, y, pressed }: { label: string; x: number; y: number; pressed?: boolean }) {
  return <div className={`analogBox ${pressed ? "pressed" : ""}`}><b>{label}</b><span>X {x.toFixed(3)}</span><span>Y {y.toFixed(3)}</span>{pressed && <strong>CLICK</strong>}</div>;
}

function InfoBanner({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="infoBanner"><span>i</span><div><b>{title}</b><p>{children}</p></div></div>;
}
function EmptyConfig() { return <div className="emptyState"><span>◎</span><h2>No configuration loaded</h2><p>Connect ARMOR-X Pro from the top-right button first.</p></div>; }
function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return <div className="modalBackdrop" onMouseDown={onClose}><div className="modal" onMouseDown={(e) => e.stopPropagation()}>{children}</div></div>;
}
function humanize(value: string) { return value.replace(/([A-Z])/g, " $1").replace(/^./, (m) => m.toUpperCase()); }
function shortHash(value?: string) { return value ? `${value.slice(0, 10)}…${value.slice(-8)}` : "—"; }

export default App;
