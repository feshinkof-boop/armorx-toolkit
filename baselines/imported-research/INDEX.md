# baselines/imported-research — frozen Phase-1 snapshot (index)

Read-only freeze of the pre-existing ArmorX research. Source repos/dirs were **not**
modified. Every file below is covered by `SHA256SUMS` in this directory:

    cd /home/salamanka/armorx-lab/baselines/imported-research && sha256sum -c SHA256SUMS

## Structure

    README.md                             <- the research pass README (copied artifact)
    <research artifacts, flat>            <- docs/static pass for MYGT 4.0.8
    docs/mygt-4.0.8-reconciliation.md     <- canonical reconciliation doc
    pcap/                                 <- existing server-side PCAPs (HTTP/TCP captures)
    captures/                             <- previous live capture / handoff bundle (2026-09-23)
    patches/                              <- git patch + bundle of the 4.0.8 research branch

## Provenance of each group

### Research artifacts (flat)
Source: `/home/salamanka/armorx-re/repo/research/mygt-4.0.8/`
(byte-identical duplicate at `/home/salamanka/armorx-re/mygt408/research/mygt-4.0.8/`;
`diff -rq` of the two trees is empty — verified).
Files: executive-report.md, live-test-plan.md, unresolved.md, command-index.md,
command-index.json, config-field-map.json, d8-macro.md, d8-test-vectors.json,
key-id-table.md, fc-dpi.md, fc-dpi-test-vectors.json, ff-lighting.md,
ff-lighting-test-vectors.json, turbo.md, gyro-trigger-stick.md, old-vs-mygt-4.0.8.md,
old-vs-mygt-4.0.8.json, device-model-matrix.md, device-model-matrix.json,
config-144-reconstruction.md, provenance.md, ble-architecture.md, api-map.md, README.md.

### docs/mygt-4.0.8-reconciliation.md
Source: `/home/salamanka/armorx-re/repo/docs/mygt-4.0.8-reconciliation.md`.

### pcap/ (existing PCAPs)
| copy | source |
|---|---|
| v1_handoff10_PCAPdroid_21_Sep_18_38_15.pcap | ArmorX_Config_Format_Handoff/10_pcap_config_traffic/ |
| v1_handoff10_ArmorX_HTTP_PCAP_Extract.txt | ArmorX_Config_Format_Handoff/10_pcap_config_traffic/ |
| v2_handoff_pcap_PCAPdroid_21_Sep_18_38_15.pcap | ArmorX_Config_Format_Handoff_v2/pcap/ |
| v2_handoff_pcap_ArmorX_HTTP_PCAP_Extract.txt | ArmorX_Config_Format_Handoff_v2/pcap/ |
| PCAPdroid_22_Sep_17_44_31.pcap | ~/Downloads/ |
The two 21-Sep PCAPdroid files are the same capture from two handoff bundles (same size);
kept as separate copies with source-prefixed names for provenance clarity.

### captures/ (previous live captures / handoff zip)
Source: `/home/salamanka/armorx_handoff/project/current_handoff/`
ArmorX_Pro_ReadOnly_Probe_2026-09-23.zip, PCAPdroid_23_Sep_20_53_43.pcap,
HANDOFF_REPORT_2026-09-23.md, PROJECT_STATE_2026-09-23.json.

### patches/ (research branch freeze)
Source: `/home/salamanka/armorx-re/mygt408/`
mygt-4.0.8-research.patch (606305 B), mygt-4.0.8-branch.bundle (246380 B).
Repo: https://github.com/feshinkof-boop/armorx-toolkit, branch research/mygt-4.0.8, HEAD dbe2ce7.

## Not copied (intentionally)
Raw APK originals, blutter output trees, and other working dirs — those are handled
elsewhere in the lab (`apk/original/`, `static/blutter/`). This directory is only the
frozen *research documents + captures + patches*.
