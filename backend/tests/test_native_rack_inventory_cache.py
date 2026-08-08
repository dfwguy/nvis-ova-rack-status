from __future__ import annotations

from pathlib import Path

import native_status


def test_rack_inventory_is_cached_but_device_workers_remain_independent(monkeypatch):
    calls: list[int] = []
    clock = iter((100.0, 110.0, 111.0))

    monkeypatch.setenv("RACK_NATIVE_RACK_LIST_TTL_SEC", "900")
    monkeypatch.setattr(native_status.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(
        native_status,
        "_cmsh_rack_list",
        lambda: calls.append(1) or ["wh1j1", "wh1j15"],
    )

    state = native_status.NativeRackTableState("test", Path("/tmp"))
    state.refresh_racks_blocking()
    state.refresh_racks_blocking()

    assert calls == [1]
    assert state.racks == ["wh1j1", "wh1j15"]


def test_rack_inventory_refreshes_after_ttl(monkeypatch):
    inventories = iter((["wh1j1"], ["wh1j1", "wh1j15"]))
    clock = iter((100.0, 1001.0))

    monkeypatch.setenv("RACK_NATIVE_RACK_LIST_TTL_SEC", "900")
    monkeypatch.setattr(native_status.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(native_status, "_cmsh_rack_list", lambda: list(next(inventories)))

    state = native_status.NativeRackTableState("test", Path("/tmp"))
    state.refresh_racks_blocking()
    state.refresh_racks_blocking()

    assert state.racks == ["wh1j1", "wh1j15"]


def test_failed_refresh_keeps_last_good_inventory(monkeypatch):
    inventories = iter((["wh1j1"], []))
    clock = iter((100.0, 1001.0))

    monkeypatch.setenv("RACK_NATIVE_RACK_LIST_TTL_SEC", "900")
    monkeypatch.setattr(native_status.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(native_status, "_cmsh_rack_list", lambda: list(next(inventories)))

    state = native_status.NativeRackTableState("test", Path("/tmp"))
    state.refresh_racks_blocking()
    state.refresh_racks_blocking()

    assert state.racks == ["wh1j1"]
