"""Transport tests: everything runs against the mock, nothing touches devices."""

import pytest

from armorx import transport as T


def test_mock_transport_returns_scripted_chunks():
    mock = T.replay([b"one", b"two"])
    assert mock.read() == b"one"
    assert mock.read() == b"two"


def test_mock_transport_raises_when_exhausted():
    with pytest.raises(T.TransportError, match="no scripted data"):
        T.replay([]).read()


def test_mock_transport_is_read_only_by_default():
    with pytest.raises(T.WriteRefused, match="read-only"):
        T.MockTransport().write(b"x")


def test_mock_transport_records_opted_in_writes():
    mock = T.MockTransport(read_only=False)
    assert mock.write(b"ab") == 2
    assert mock.writes == [b"ab"]


def test_close_makes_reads_fail():
    mock = T.replay([b"one"])
    mock.close()
    with pytest.raises(T.TransportError, match="closed"):
        mock.read()


def test_read_size_is_respected():
    assert T.replay([b"abcdef"]).read(3) == b"abc"


def test_hidraw_missing_node_is_a_clear_error(tmp_path):
    with pytest.raises(T.TransportError, match="does not exist"):
        T.open_hidraw(str(tmp_path / "hidraw9"))


def test_hidraw_writes_are_refused(tmp_path):
    node = tmp_path / "hidraw2"
    node.write_bytes(b"")
    handle = T.open_hidraw(str(node))
    try:
        with pytest.raises(T.WriteRefused):
            handle.write(b"x")
    finally:
        handle.close()


def test_drive_walks_a_transport_until_exhausted():
    payloads = T.drive(T.replay([b"a", b"b"]), lambda chunk: chunk.upper())
    assert payloads == [b"A", b"B"]
