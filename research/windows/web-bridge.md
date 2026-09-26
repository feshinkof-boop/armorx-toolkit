# Windows Assistant web/ActiveX bridge inventory — 2026-09-25

Preserves and extends prior findings (research-status-2026-09-25.md: the configured
IE page `http://app.mojhon.cn/HTML/Analysis/BigBigWonAssistant.51la.html` now serves
only an analytics stub; `CWebBrowserEx::Invoke` / `window.external` exist). This pass
enumerates the native data model reachable through the bridge without executing anything.

## Native JSON layer (PROVEN_STATIC: WndMgr.dll strings)

`CJsonCreator` in WndMgr.dll (Assistant 1.0.6.1) builds the same server JSON as the
Android app, against the same host:

```
http://m.bigbigwon.com:8080/dev/{register,userLogin,queryConfigList,addConfig,
  changeConfig,renameConfig,delConfig,shareConfig,importShareConfig,queryMacroList,
  addMacro,changeMacro,delMacro,queryFirewareList}
```

Per-method parameter names recovered from the string table:

| CJsonCreator method | JSON fields |
|---|---|
| Regist | devUuid, currentVersion, upgradeLastTime, userPass, checkCode |
| UserLogin | deviceName, versions, phoneVersion, appVersion, phoneUuid, phoneModel, userPass, phoneLocation, email |
| GetConfigList | configType, userId, firmwareVersion, pageNum, phoneUuid, devUuid |
| RenameConfig / DeleteConfig | configName, userId, phoneUuid, devUuid |
| AddConfig / ChangeConfig / ShareConfig / ImportShareConfig | configType, configName, configJson, firmwareVersion, zkmVersion, deviceModel, phoneUuid, devUuid, shareCode |
| GetMacroList | pageNum, userId, phoneUuid, devUuid |
| AddMacro / ChangeMacro | runKeyName, isRepeat, inUse, runKey, macroJson, repeatTime, macroName, phoneUuid, devUuid |
| DeleteMacro | shareCode, phoneUuid, devUuid |
| GetFirmwareList | (light strings adjacent: lightZoneR3, speed, …) |
| LightInfo4Gale2 / LightInfo4Rainbow3 | per-device lighting JSON |

This is direct cross-platform corroboration of the Android server API map: both clients
share one protocol. The Android 2.24 app adds /dev/queryGameList; the Windows
Assistant 1.0.6.1 does not contain it (older surface).

Also recovered (same string cluster): the OSS download endpoints used by the
assistant for self/firmware updates
(`bigbig-won-cn.oss-cn-shanghai.aliyuncs.com/Support/PC_app/*`,
`.../Firmware/Tool/BurnTool_LastVersionNo.*`, MSY/BlackShark variants) — consistent
with the BurnTool DFU flow already documented for DevMgr.dll.

## Bridge reachability (preserved from prior live/static work)

- `CWebBrowserEx::Invoke` + `window.external` exist in the running Assistant
  (prior live observation).
- The historical page that drove the per-device session is no longer served;
  the current configured URL returns an analytics stub only.
- The native side this bridge would call (CJsonCreator + DevMgr device objects)
  is fully present; only the page-side caller is gone.

## Implication for the Windows session-init question

The web bridge is not the only path to the device layer: the assistant's own
native code contains the complete client (JSON + USB). The unresolved question is
which native entry point the historical page invoked; that remains UNKNOWN until
a historical page copy is found or the native callers of DevMgr's device factory
are traced further.
