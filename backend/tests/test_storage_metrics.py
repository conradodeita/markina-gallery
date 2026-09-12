from pathlib import Path

import pytest

from app import storage_metrics


def _configure_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, ...]:
    roots = tuple(tmp_path / name for name in ("source", "derivatives", "history"))
    for root in roots:
        root.mkdir()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(roots[0]))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(roots[1]))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(roots[2]))
    storage_metrics.clear_storage_usage_cache()
    return roots


def test_measure_photo_storage_sums_regular_files_without_following_symlinks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, derivatives, history = _configure_roots(monkeypatch, tmp_path)
    (source / "one.jpg").write_bytes(b"a" * 11)
    (derivatives / "nested").mkdir()
    (derivatives / "nested" / "preview.jpg").write_bytes(b"b" * 17)
    (history / "confirmed.jpg").write_bytes(b"c" * 23)

    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"x" * 101)
    try:
        (source / "outside-link.jpg").symlink_to(outside)
    except OSError:
        pass

    measured = storage_metrics.measure_photo_storage()
    assert measured.available is True
    assert measured.bytes == 51


def test_measure_photo_storage_reports_zero_and_expires_cache_in_at_most_30_seconds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, _, _ = _configure_roots(monkeypatch, tmp_path)
    clock = iter((100.0, 129.9, 130.0))
    monkeypatch.setattr(storage_metrics, "monotonic", lambda: next(clock))

    assert storage_metrics.measure_photo_storage().bytes == 0
    (source / "later.jpg").write_bytes(b"new")
    assert storage_metrics.measure_photo_storage().bytes == 0
    assert storage_metrics.measure_photo_storage().bytes == 3


def test_measure_photo_storage_returns_no_partial_total_on_read_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_roots(monkeypatch, tmp_path)

    def fail_scan(_root: Path) -> int:
        raise PermissionError("path must not leak")

    monkeypatch.setattr(storage_metrics, "_scan_regular_files", fail_scan)
    measured = storage_metrics.measure_photo_storage()
    assert measured.available is False
    assert measured.bytes is None
