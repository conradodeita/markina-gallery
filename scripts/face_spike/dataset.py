"""Build and safely remove the synthetic-only corpus used by the facial spike."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

MARKER_NAME = ".markina-face-spike.json"
MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = 1
IDENTITY_COUNT = 16
SEED = 20260905


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise ValueError("O diretório do spike não pode ser a raiz nem o diretório pessoal.")
    return resolved


def _cell(sheet: Image.Image, identity_index: int) -> Image.Image:
    column = identity_index % 4
    row = identity_index // 4
    left = round(column * sheet.width / 4)
    right = round((column + 1) * sheet.width / 4)
    top = round(row * sheet.height / 4)
    bottom = round((row + 1) * sheet.height / 4)
    inset = max(4, min(right - left, bottom - top) // 80)
    return sheet.crop((left + inset, top + inset, right - inset, bottom - inset)).convert("RGB")


def _augment_face(face: Image.Image, rng: random.Random, variant: int) -> tuple[Image.Image, str]:
    scenario = ("clean", "lighting", "blur", "low_resolution", "occlusion")[variant % 5]
    rendered = face.copy()
    rendered = ImageEnhance.Brightness(rendered).enhance(rng.uniform(0.72, 1.28))
    rendered = ImageEnhance.Contrast(rendered).enhance(rng.uniform(0.82, 1.20))
    rendered = rendered.rotate(rng.uniform(-10, 10), resample=Image.Resampling.BICUBIC)
    if scenario == "blur":
        rendered = rendered.filter(ImageFilter.GaussianBlur(radius=rng.uniform(1.0, 2.4)))
    elif scenario == "low_resolution":
        small_edge = rng.randint(72, 112)
        small = rendered.resize((small_edge, small_edge), Image.Resampling.BILINEAR)
        rendered = small.resize(rendered.size, Image.Resampling.BILINEAR)
    elif scenario == "occlusion":
        draw = ImageDraw.Draw(rendered)
        y = int(rendered.height * rng.uniform(0.60, 0.70))
        draw.rectangle(
            (int(rendered.width * 0.28), y, int(rendered.width * 0.72), y + 12),
            fill=(75, 75, 75),
        )
    if variant % 7 == 0:
        pixels = np.asarray(rendered, dtype=np.int16)
        noise_rng = np.random.default_rng(SEED + variant)
        noise = noise_rng.normal(0, 4.0, size=pixels.shape)
        rendered = Image.fromarray(np.clip(pixels + noise, 0, 255).astype(np.uint8), "RGB")
    return rendered, scenario


def _event_frame(face: Image.Image, rng: random.Random) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (960, 720),
        color=(rng.randint(40, 120), rng.randint(40, 120), rng.randint(40, 120)),
    )
    target_width = rng.randint(260, 430)
    target_height = round(face.height * target_width / face.width)
    resized = face.resize((target_width, target_height), Image.Resampling.LANCZOS)
    x = rng.randint(20, canvas.width - resized.width - 20)
    y = rng.randint(10, max(10, canvas.height - resized.height - 10))
    canvas.paste(resized, (x, y))
    return canvas


def _save_jpeg(image: Image.Image, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=88, optimize=True)
    return {
        "path": path.as_posix(),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _relative(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    copy = dict(entry)
    copy["path"] = Path(copy["path"]).relative_to(root).as_posix()
    return copy


def build_dataset(front_sheet: Path, angle_sheet: Path, output: Path, seed: int = SEED) -> dict[str, Any]:
    root = _safe_output(output)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError("O diretório de saída deve estar ausente ou vazio.")
    root.mkdir(parents=True, exist_ok=True)
    marker = {
        "kind": "markina-face-spike",
        "schema_version": SCHEMA_VERSION,
        "synthetic_only": True,
    }
    (root / MARKER_NAME).write_text(json.dumps(marker, indent=2), encoding="utf-8")

    with Image.open(front_sheet) as opened:
        front = opened.convert("RGB")
    with Image.open(angle_sheet) as opened:
        angle = opened.convert("RGB")
    if front.width < 800 or front.height < 800 or angle.width < 800 or angle.height < 800:
        raise ValueError("As folhas sintéticas devem ter pelo menos 800 × 800 pixels.")

    rng = random.Random(seed)
    identities = [f"fictional-adult-{index + 1:02d}" for index in range(IDENTITY_COUNT)]
    front_cells = [_cell(front, index) for index in range(IDENTITY_COUNT)]
    angle_cells = [_cell(angle, index) for index in range(IDENTITY_COUNT)]
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "synthetic_only": True,
        "seed": seed,
        "identities": identities,
        "events": {"event-a": [], "event-b": []},
        "queries": [],
    }

    for identity_index, identity in enumerate(identities):
        for pose_name, cell in (("front", front_cells[identity_index]), ("angle", angle_cells[identity_index])):
            path = root / "queries" / f"{identity}-{pose_name}.jpg"
            entry = _relative(_save_jpeg(cell, path), root)
            entry.update({"identity": identity, "pose": pose_name, "expected_faces": 1})
            manifest["queries"].append(entry)

        for variant in range(30):
            source = front_cells[identity_index] if variant % 2 == 0 else angle_cells[identity_index]
            augmented, scenario = _augment_face(source, rng, variant)
            frame = _event_frame(augmented, rng)
            path = root / "event-a" / f"{identity}-v{variant + 1:02d}.jpg"
            entry = _relative(_save_jpeg(frame, path), root)
            entry.update(
                {
                    "identities": [identity],
                    "expected_faces": 1,
                    "scenario": scenario,
                }
            )
            manifest["events"]["event-a"].append(entry)

    for group_index in range(16):
        selected = [(group_index + offset * 4) % IDENTITY_COUNT for offset in range(4)]
        canvas = Image.new("RGB", (1280, 720), color=(68, 72, 78))
        positions = ((25, 220), (340, 220), (655, 220), (970, 220))
        names: list[str] = []
        for slot, identity_index in enumerate(selected):
            cell = angle_cells[identity_index] if slot % 2 else front_cells[identity_index]
            resized = cell.resize((280, 280), Image.Resampling.LANCZOS)
            canvas.paste(resized, positions[slot])
            names.append(identities[identity_index])
        path = root / "event-a" / f"group-{group_index + 1:02d}.jpg"
        entry = _relative(_save_jpeg(canvas, path), root)
        entry.update({"identities": names, "expected_faces": 4, "scenario": "group"})
        manifest["events"]["event-a"].append(entry)

    for negative_index in range(8):
        canvas = Image.new("RGB", (960, 720), color=(35 + negative_index * 8, 55, 75))
        draw = ImageDraw.Draw(canvas)
        for shape in range(12):
            x = (shape * 73 + negative_index * 31) % 850
            y = (shape * 47 + negative_index * 29) % 610
            draw.rectangle((x, y, x + 70, y + 55), outline=(180, 170, 150), width=4)
        path = root / "event-a" / f"negative-{negative_index + 1:02d}.jpg"
        entry = _relative(_save_jpeg(canvas, path), root)
        entry.update({"identities": [], "expected_faces": 0, "scenario": "no_face"})
        manifest["events"]["event-a"].append(entry)

    for identity_index in range(4):
        identity = identities[identity_index]
        frame = _event_frame(angle_cells[identity_index], rng)
        path = root / "event-b" / f"isolation-{identity}.jpg"
        entry = _relative(_save_jpeg(frame, path), root)
        entry.update({"identities": [identity], "expected_faces": 1, "scenario": "isolation"})
        manifest["events"]["event-b"].append(entry)

    manifest_path = root / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return verify_dataset(root)


def _load_marker(root: Path) -> dict[str, Any]:
    marker_path = root / MARKER_NAME
    if not marker_path.is_file():
        raise ValueError("Marcador de segurança do spike ausente.")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker != {
        "kind": "markina-face-spike",
        "schema_version": SCHEMA_VERSION,
        "synthetic_only": True,
    }:
        raise ValueError("Marcador de segurança do spike inválido.")
    return marker


def verify_dataset(output: Path) -> dict[str, Any]:
    root = _safe_output(output)
    _load_marker(root)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError("Manifesto do corpus ausente.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("synthetic_only") is not True:
        raise ValueError("O manifesto não declara corpus exclusivamente sintético.")
    entries = [
        *manifest["events"]["event-a"],
        *manifest["events"]["event-b"],
        *manifest["queries"],
    ]
    for entry in entries:
        candidate = (root / entry["path"]).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise ValueError(f"Arquivo ausente ou fora do corpus: {entry['path']}")
        if _sha256(candidate) != entry["sha256"]:
            raise ValueError(f"Hash divergente: {entry['path']}")
    actual_jpegs = list(root.rglob("*.jpg"))
    if len(actual_jpegs) != len(entries):
        raise ValueError("A quantidade de JPEGs diverge do manifesto.")
    return {
        "synthetic_only": True,
        "event_a_images": len(manifest["events"]["event-a"]),
        "event_b_images": len(manifest["events"]["event-b"]),
        "query_images": len(manifest["queries"]),
        "total_jpegs": len(entries),
        "identities": len(manifest["identities"]),
        "expected_event_a_faces": sum(
            entry["expected_faces"] for entry in manifest["events"]["event-a"]
        ),
    }


def clean_dataset(output: Path) -> None:
    root = _safe_output(output)
    _load_marker(root)
    shutil.rmtree(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--front-sheet", type=Path, required=True)
    build.add_argument("--angle-sheet", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--seed", type=int, default=SEED)
    for name in ("verify", "clean"):
        command = subparsers.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = build_dataset(args.front_sheet, args.angle_sheet, args.output, args.seed)
        print(json.dumps(result, indent=2))
    elif args.command == "verify":
        print(json.dumps(verify_dataset(args.output), indent=2))
    else:
        clean_dataset(args.output)
        print(json.dumps({"removed": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
