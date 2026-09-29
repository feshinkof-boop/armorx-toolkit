"""Hardware-free tests for the conservative BLE scan classification."""

from armorx import live as L


class _Adv:
    def __init__(self, local_name="", rssi=-60, service_uuids=(), manufacturer_data=None,
                 service_data=None):
        self.local_name = local_name
        self.rssi = rssi
        self.service_uuids = list(service_uuids)
        self.manufacturer_data = manufacturer_data or {}
        self.service_data = service_data or {}


class _Device:
    def __init__(self, address, name=""):
        self.address = address
        self.name = name


class _FakeScanner:
    rows: list = []

    @staticmethod
    async def discover(**kwargs):
        return {index: (device, adv)
                for index, (device, adv) in enumerate(_FakeScanner.rows)}


def _scan_with(monkeypatch, rows):
    _FakeScanner.rows = list(rows)
    monkeypatch.setattr(L, "_load_bleak", lambda: (None, _FakeScanner))
    return L.scan_ble(seconds=0.01)


def test_named_armorx_is_classified_and_the_reason_is_recorded(monkeypatch):
    import asyncio
    rows = _scan_with(monkeypatch, [(_Device("AA:BB:CC:DD:EE:01", ""),
                                     _Adv(local_name="ARMOR-X Pro_11"))])
    rows = asyncio.run(rows)
    assert rows[0]["is_armorx"] is True
    assert rows[0]["anonymous"] is False
    assert "ARMOR-X Pro" in rows[0]["candidate_reason"]


def test_anonymous_advertisement_is_never_classified_as_armorx(monkeypatch):
    import asyncio
    rows = _scan_with(monkeypatch, [(_Device("AA:BB:CC:DD:EE:02", ""), _Adv())])
    rows = asyncio.run(rows)
    assert rows[0]["is_armorx"] is False
    assert rows[0]["anonymous"] is True
    assert "cannot be classified" in rows[0]["candidate_reason"]


def test_anonymous_advertisement_still_carries_the_evidence(monkeypatch):
    import asyncio
    adv = _Adv(service_uuids=["0000ffe1-0000-1000-8000-00805f9b34fb"],
               manufacturer_data={0x5A4A: bytes.fromhex("2d5854")})
    rows = asyncio.run(_scan_with(monkeypatch, [(_Device("AA:BB:CC:DD:EE:03", ""), adv)]))
    row = rows[0]
    assert row["is_armorx"] is False                     # still conservative
    assert row["service_uuids"] == ["0000ffe1-0000-1000-8000-00805f9b34fb"]
    assert row["manufacturer_data"] == {"0x5A4A": "2d 58 54"}
    assert row["address"] == "AA:BB:CC:DD:EE:03"        # local connection use only
    assert row["candidate_reason"]


def test_manufacturer_payload_is_truncated_and_never_crashes():
    class _Odd:
        manufacturer_data = {"nope": b"\x01\x02"}
        service_data = {"u": b"\x03"}

    assert L._manufacturer_summary(_Odd()) == {}
    assert L._service_data_summary(_Odd()) == {"u": "03"}


def test_long_manufacturer_payload_is_truncated():
    class _Long:
        manufacturer_data = {0x0102: b"\xaa" * 64}
        service_data = {}

    summary = L._manufacturer_summary(_Long())
    assert "(64 bytes)" in summary["0x0102"]
    assert len(summary["0x0102"].split("...")[0].strip().split()) == 32


def test_sorting_puts_classified_candidates_first(monkeypatch):
    import asyncio
    rows = asyncio.run(_scan_with(monkeypatch, [
        (_Device("AA:BB:CC:DD:EE:04", ""), _Adv()),
        (_Device("AA:BB:CC:DD:EE:05", ""), _Adv(local_name="ARMOR-X Pro_2")),
    ]))
    assert rows[0]["is_armorx"] is True
