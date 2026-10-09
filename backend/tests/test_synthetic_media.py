from hashlib import sha256

from PIL import Image
import pytest

from tests.synthetic_media import (
    SyntheticMediaError,
    pilot_photo_bytes,
    verify_pilot_media,
)


def test_manifest_includes_only_byte_identical_fixture_media_without_modifying_sources(tmp_path):
    trusted = tmp_path / "synthetic" / "account-a.jpg"
    trusted.parent.mkdir()
    trusted.write_bytes(pilot_photo_bytes(0, 2))
    before = sha256(trusted.read_bytes()).hexdigest()

    untrusted = tmp_path / "synthetic" / "unverified.jpg"
    Image.new("RGB", (256, 192), (12, 34, 56)).save(untrusted, "JPEG", quality=80)

    manifest = verify_pilot_media(tmp_path)

    assert len(manifest.verified) == 1
    assert manifest.verified[0].relative_path == "synthetic/account-a.jpg"
    assert manifest.verified[0].sha256 == before
    assert manifest.verified[0].mime == "image/jpeg"
    assert (manifest.verified[0].width, manifest.verified[0].height) == (256, 192)
    assert manifest.rejected_count == 1
    assert sha256(trusted.read_bytes()).hexdigest() == before


def test_manifest_rejects_media_root_symlinks_fail_closed(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "outside.jpg"
    external.write_bytes(pilot_photo_bytes(0, 0))
    link = root / "linked.jpg"
    try:
        link.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(SyntheticMediaError, match="media_symlink_forbidden"):
        verify_pilot_media(root)
