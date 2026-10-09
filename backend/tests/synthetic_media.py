"""Canonical synthetic media and byte-level provenance checks for the pilot corpus."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


class SyntheticMediaError(ValueError):
    """Raised when the media root cannot be inspected safely."""


def pilot_photo_bytes(account_index: int, photo_index: int) -> bytes:
    """Return exactly the JPEG bytes used by the synthetic 2×3 pilot fixture."""
    if account_index not in (0, 1) or photo_index not in range(6):
        raise ValueError("pilot_photo_index_out_of_range")
    image = Image.new("RGB", (256, 192), (30 + account_index * 80, 40 + photo_index * 20, 90))
    ImageDraw.Draw(image).rectangle(
        (32, 32, 120 + photo_index * 8, 150), fill=(190, 150, 80)
    )
    payload = BytesIO()
    image.save(payload, "JPEG", quality=80)
    return payload.getvalue()


@dataclass(frozen=True)
class VerifiedMedia:
    relative_path: str
    sha256: str
    mime: str
    width: int
    height: int


@dataclass(frozen=True)
class MediaManifest:
    verified: tuple[VerifiedMedia, ...]
    rejected_count: int
    manifest_sha256: str


def verify_pilot_media(root: Path) -> MediaManifest:
    """Read media without mutation and include only byte-identical fixture JPEGs."""
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise SyntheticMediaError("media_root_unavailable") from exc
    if not resolved_root.is_dir():
        raise SyntheticMediaError("media_root_not_directory")

    fixture_hashes = {
        sha256(pilot_photo_bytes(account_index, photo_index)).hexdigest()
        for account_index in range(2)
        for photo_index in range(6)
    }
    verified: list[VerifiedMedia] = []
    rejected = 0
    try:
        paths = sorted(resolved_root.rglob("*"))
        for path in paths:
            if path.is_symlink():
                raise SyntheticMediaError("media_symlink_forbidden")
            if not path.is_file():
                continue
            resolved_path = path.resolve(strict=True)
            if resolved_root not in resolved_path.parents:
                raise SyntheticMediaError("media_path_escape")
            try:
                content = path.read_bytes()
                digest = sha256(content).hexdigest()
                with Image.open(BytesIO(content)) as image:
                    image.verify()
                with Image.open(BytesIO(content)) as image:
                    media_format = image.format
                    width, height = image.size
            except Exception:  # noqa: BLE001 -- reject unreadable files without leaking paths/data.
                rejected += 1
                continue
            if (
                path.suffix.lower() not in {".jpg", ".jpeg"}
                or media_format != "JPEG"
                or (width, height) != (256, 192)
                or digest not in fixture_hashes
            ):
                rejected += 1
                continue
            verified.append(
                VerifiedMedia(
                    relative_path=path.relative_to(resolved_root).as_posix(),
                    sha256=digest,
                    mime="image/jpeg",
                    width=width,
                    height=height,
                )
            )
    except SyntheticMediaError:
        raise
    except OSError as exc:
        raise SyntheticMediaError("media_read_failed") from exc

    manifest_bytes = "\n".join(
        f"{item.relative_path}\t{item.sha256}\t{item.mime}\t{item.width}x{item.height}"
        for item in verified
    ).encode("utf-8")
    return MediaManifest(
        verified=tuple(verified),
        rejected_count=rejected,
        manifest_sha256=sha256(manifest_bytes).hexdigest(),
    )


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media_root", type=Path)
    args = parser.parse_args()
    manifest = verify_pilot_media(args.media_root)
    print(
        json.dumps(
            {
                "schema": "pyp-synthetic-media-manifest/v1",
                "verified_file_count": len(manifest.verified),
                "rejected_file_count": manifest.rejected_count,
                "mime": "image/jpeg",
                "dimensions": "256x192",
                "manifest_sha256": manifest.manifest_sha256,
                "originals_modified": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
