import os
from pathlib import Path

import pytest

from nova_eink_display.metrics import Metrics
from nova_eink_display.state import FILENAME, WearState, state_path

PAYLOAD = {"refresh_total": {"full": 2, "partial": 7}, "starts_total": 3}
EMPTY = {"refresh_total": {"full": 0, "partial": 0}, "starts_total": 0}


@pytest.fixture
def store(tmp_path: Path) -> WearState:
    return WearState(str(tmp_path / FILENAME))


def test_an_empty_state_directory_disables_persistence() -> None:
    assert state_path("") is None


def test_only_the_first_systemd_directory_is_used() -> None:
    assert state_path("/a:/b") == os.path.join("/a", FILENAME)


def test_a_disabled_store_is_inert() -> None:
    disabled = WearState(None)

    assert disabled.load() == {}
    disabled.save(PAYLOAD)
    assert not disabled.writable


def test_a_missing_file_loads_as_empty(store: WearState) -> None:
    assert store.load() == {}


def test_a_payload_round_trips(store: WearState) -> None:
    store.save(PAYLOAD)
    assert store.load() == PAYLOAD


def test_save_replaces_the_previous_payload(store: WearState) -> None:
    store.save(PAYLOAD)
    store.save({"starts_total": 4})
    assert store.load() == {"starts_total": 4}


def test_save_leaves_no_temporary_files(store: WearState, tmp_path: Path) -> None:
    store.save(PAYLOAD)
    assert [entry.name for entry in tmp_path.iterdir()] == [FILENAME]


@pytest.mark.parametrize(
    ("description", "contents"),
    [
        ("truncated by a power cut", '{"starts_total": 4'),
        ("not an object", "[1, 2, 3]"),
        ("empty", ""),
    ],
)
def test_unusable_contents_load_as_empty(
    tmp_path: Path, store: WearState, description: str, contents: str
) -> None:
    (tmp_path / FILENAME).write_text(contents, encoding="utf-8")
    assert store.load() == {}, description


def test_an_unwritable_directory_stops_further_saves(tmp_path: Path) -> None:
    store = WearState(str(tmp_path / "missing" / FILENAME))

    store.save(PAYLOAD)
    assert not store.writable
    assert store.load() == {}


def test_restore_seeds_the_lifetime_counters() -> None:
    metrics = Metrics()
    metrics.restore({"full": 5, "partial": 11}, 9)
    metrics.record_start(persisted=True)

    text = metrics.render()
    assert 'eink_refresh_total{kind="full"} 5' in text
    assert 'eink_refresh_total{kind="partial"} 11' in text
    assert "eink_starts_total 10" in text
    assert "eink_wear_persisted 1" in text


def test_a_snapshot_carries_the_counters_forward() -> None:
    metrics = Metrics()
    metrics.restore({"full": 5, "partial": 11}, 9)
    metrics.record_start(persisted=True)
    metrics.record_refresh("full", 0)

    assert metrics.snapshot() == {
        "refresh_total": {"full": 6, "partial": 11},
        "starts_total": 10,
    }


@pytest.mark.parametrize(
    "garbage",
    [None, [1, 2], "12", 3.5, {"full": -3, "partial": 1.5}, {"full": True}],
    ids=["missing", "list", "string", "float", "negative-and-float", "bool"],
)
def test_restore_rejects_garbage(garbage: object) -> None:
    metrics = Metrics()
    metrics.restore(garbage, garbage)

    assert metrics.snapshot() == EMPTY


def test_a_start_is_still_counted_without_persistence() -> None:
    metrics = Metrics()
    metrics.record_start(persisted=False)

    assert "eink_starts_total 1" in metrics.render()
    assert "eink_wear_persisted 0" in metrics.render()
