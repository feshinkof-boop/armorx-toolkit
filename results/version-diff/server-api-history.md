# Server-API history — 2.22.0901 / 2.23.0609 / 2.24.0919 / 4.0.8

Four-way endpoint + host table. Source of every cell is the respective build's Dart AOT string pool
(`blutter_out/pp.txt`), read in this pass; the 2.22 column is new here.

Commands:

```bash
for t in \
  /home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out \
  /home/salamanka/armorx/re/blutter_out \
  /home/salamanka/armorx/re/v224/blutter_out \
  /home/salamanka/armorx-re/mygt408/blutter_out ; do
    printf '== %s\n' "$t"
    grep -a -oE '"/dev/[a-zA-Z]+"' "$t/pp.txt" | tr -d '"' | sort -u
    grep -a -oE 'https://[a-z0-9.-]+\.aliyuncs\.com' "$t/pp.txt" | sort -u
done
```

## Endpoint table

| endpoint | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|:--:|:--:|:--:|:--:|
| `/dev/register` | ✅ | ✅ | ✅ | ✅ |
| `/dev/userLogin` | ✅ | ✅ | ✅ | ✅ |
| `/dev/queryConfigList` | ✅ | ✅ | ✅ | ✅ |
| `/dev/addConfig` | ✅ | ✅ | ✅ | ✅ |
| `/dev/changeConfig` | ✅ | ✅ | ✅ | ✅ |
| `/dev/renameConfig` | ✅ | ✅ | ✅ | ✅ |
| `/dev/delConfig` | ✅ | ✅ | ✅ | ✅ |
| `/dev/queryMacroList` | ✅ | ✅ | ✅ | ✅ |
| `/dev/addMacro` | ✅ | ✅ | ✅ | ✅ |
| `/dev/changeMacro` | ✅ | ✅ | ✅ | ✅ |
| `/dev/delMacro` | ✅ | ✅ | ✅ | ✅ |
| `/dev/setConfig` | ✅ | ✅ | ✅ | ✅ |
| `/dev/queryDefaultConfig` | ✅ | ✅ | ✅ | ❌ |
| `/dev/shareConfig` | ❌ | ✅ | ✅ | ✅ |
| `/dev/importShareConfig` | ❌ | ✅ | ✅ | ✅ |
| `/dev/queryGameList` | ❌ | ❌ | ✅ | ❌ |
| **count** | **13** | **15** | **16** | **14** |

### The two questions posed

* **Did 2.22 have `queryDefaultConfig`?** **Yes** — present at `pp+0x46230`
  (`"/dev/queryDefaultConfig"`). It survives through 2.23 and 2.24 and is dropped only by 4.0.8.
* **Did 2.22 have `queryGameList`?** **No.** `grep -c queryGameList` = 0 in the 2.22, 2.23 and 4.0.8
  pools; it exists **only in 2.24** (`"/dev/queryGameList"`, 1 hit). So the premise "the later builds
  lost queryGameList" is **CONTRADICTED**: it is a 2.24-only endpoint that 2.22 never had.
* **Any endpoint 2.22 has that no later build has?** **No.** Every 2.22 endpoint is a strict subset
  of 2.23's set. 2.22 is the *base*; 2.23 **added** `shareConfig` + `importShareConfig`, 2.24 added
  `queryGameList`, and 4.0.8 **removed** `queryDefaultConfig` and `queryGameList`.

## Host history

| host | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|:--:|:--:|:--:|:--:|
| `http://m.bigbigwon.com:8080` (API base) | ✅ | ✅ | ✅ | ✅ |
| `bigbig-won-cn.oss-cn-shanghai.aliyuncs.com` | ✅ | ✅ | ✅ | ✅ |
| `bigbigwon-jp.oss-ap-northeast-1.aliyuncs.com` | ✅ | ✅ | ✅ | ✅ |
| `bigwon-us.oss-us-west-1.aliyuncs.com` | ✅ | ✅ | ✅ | ✅ |
| `bigwon-germany.oss-eu-central-1.aliyuncs.com` | ❌ | ✅ | ✅ | ✅ |
| `www.bigbigwon.com` / `www.bigbigwon.cn` / `jp.` / `kr.bigbigwon.com` | ✅ | ✅ | ✅ | ✅ |

Port: only `:8080`, on the API base, in every build. No IPv4 literal in any build.

## Evidence labels

All cells **PROVEN STATIC** (string-pool literals, exact commands above). The 4.0.8 column is
re-derived here from `~/armorx-re/mygt408/blutter_out/pp.txt`, not copied from the earlier research.

## Note on the prior four-way matrix

`results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.md` lists every 2.22 cell as
`MISSING_ARTIFACT` because it was generated before this APK was frozen. This file and
`apk/manifests/2.22.0901.json` supersede that row.