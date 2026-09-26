# Server / community API map — cross-client reconciliation — 2026-09-25

Unified from three static sources: Android 2.23 pp.txt, Android 2.24 pp.txt
(Blutter string pools), and Windows Assistant 1.0.6.1 WndMgr.dll CJsonCreator
string table. All PROVEN_STATIC. Host for all /dev endpoints:
`http://m.bigbigwon.com:8080` (both platforms).

## Endpoint matrix

| Endpoint | Android 2.23 | Android 2.24 | Windows 1.0.6.1 |
|---|---|---|---|
| /dev/register | yes | yes | yes |
| /dev/userLogin | yes | yes | yes |
| /dev/queryConfigList | yes | yes | yes |
| /dev/addConfig | yes | yes | yes |
| /dev/changeConfig | yes | yes | yes |
| /dev/renameConfig | yes | yes | yes |
| /dev/delConfig | yes | yes | yes |
| /dev/shareConfig | yes | yes | yes |
| /dev/importShareConfig | yes | yes | yes |
| /dev/queryMacroList | yes | yes | yes |
| /dev/addMacro | yes | yes | yes |
| /dev/changeMacro | yes | yes | yes |
| /dev/delMacro | yes | yes | yes |
| /dev/queryDefaultConfig | yes | yes | no |
| /dev/setConfig | yes | yes | no |
| /dev/queryGameList | no | **yes (new)** | no |
| /dev/queryFirewareList | no | no | **yes (Windows only)** |

Notes:
- The Windows spelling "queryFirewareList" (missing 'm') is verbatim from the binary.
- Parameter names per endpoint (Windows CJsonCreator table, corroborated by the
  Android JSON builders): phoneUuid, devUuid, userId, pageNum, configType,
  configName, configJson, firmwareVersion, zkmVersion, deviceModel, shareCode,
  runKey, runKeyName, isRepeat, repeatTime, macroName, macroJson, inUse,
  devModel, currentVersion, userPass, checkCode, phoneModel, phoneVersion,
  appVersion, phoneLocation, email.
- Captured live traffic (sanitized_wire_fixtures.json) confirms the shape of
  queryConfigList {phoneUuid, devUuid, pageNum, configType:1}, importShareConfig
  {shareCode}, addMacro (macroJson triple-nesting) on 2.23.
- Windows-only extra URLs (assistant self-update / firmware):
  `https://bigbig-won-cn.oss-cn-shanghai.aliyuncs.com/Support/PC_app/...`,
  `.../Firmware/Tool/BurnTool_LastVersionNo.*`.
