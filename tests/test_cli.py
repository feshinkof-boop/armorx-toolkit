import json
from pathlib import Path

from armorx import __version__
from armorx.cli import main
from armorx.config import fresh


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert __version__ in capsys.readouterr().out


def test_config_map_command(tmp_path: Path):
    source = tmp_path / "config.json"
    output = tmp_path / "mapped.json"
    source.write_text(json.dumps(fresh()), encoding="utf-8")

    rc = main([
        "config",
        "map",
        str(source),
        "M1=A",
        "M2=B",
        "-o",
        str(output),
    ])

    assert rc == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data[112 + 23] == 0
    assert data[112 + 24] == 1


def test_macro_build_command(tmp_path: Path):
    dsl = tmp_path / "combo.txt"
    output = tmp_path / "macro.json"
    dsl.write_text(
        "@name CLI Test\n"
        "@trigger M1\n"
        "@mode tap\n"
        "A 80 50\n"
        "B+RT 120 70\n",
        encoding="utf-8",
    )

    rc = main(["macro", "build", str(dsl), "-o", str(output)])

    assert rc == 0
    obj = json.loads(output.read_text(encoding="utf-8"))
    assert obj["macroName"] == "CLI Test"
    assert obj["runKey"] == 23
    assert obj["isRepeat"] == 1


def test_community_list_dry_run(tmp_path: Path):
    output = tmp_path / "request.json"

    rc = main([
        "community",
        "list",
        "--phone-uuid",
        "phone",
        "--dev-uuid",
        "device",
        "--dry-run",
        "-o",
        str(output),
    ])

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {
        "phoneUuid": "phone",
        "devUuid": "device",
        "pageNum": 1,
        "configType": 1,
    }


def test_config_keys_reports_guide_as_proven_live(capsys):
    rc = main(["config", "keys"])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    guide = next(row for row in rows if row["id"] == 12)
    assert guide == {"id": 12, "name": "GUIDE", "status": "proven_live"}
