"""Inventário e limpeza exclusiva. Execute com módulo desligado e worker parado."""

import argparse
import json
from uuid import UUID

from sqlalchemy import delete, func, select

from app.auth import PreviewAdjustment, SessionLocal
from app.media import derivatives_root
from app.preview_adjustment.service import result_path, settings


def photo_files(photo_id: UUID):
    directory = result_path(photo_id, str(UUID(int=0))).parent
    if not directory.exists():
        return []
    files = []
    for entry in directory.iterdir():
        try:
            expected = result_path(photo_id, entry.stem)
            if entry == expected and entry.is_file() and not entry.is_symlink():
                files.append(entry)
        except ValueError:
            continue
    return files


def inventory():
    root = derivatives_root()
    files = []
    if root.exists():
        for photo_directory in root.iterdir():
            if not photo_directory.is_dir() or photo_directory.is_symlink():
                continue
            try:
                photo_id = UUID(photo_directory.name)
            except ValueError:
                continue
            files.extend(photo_files(photo_id))
    return files


def cleanup(db, *, execute: bool = False, worker_stopped: bool = False):
    config = settings(db, lock=True)
    files = inventory()
    report = {
        "files": len(files),
        "bytes": sum(p.stat().st_size for p in files),
        "records": db.scalar(select(func.count()).select_from(PreviewAdjustment)),
        "deleted": False,
    }
    if execute:
        if (config and config.enabled) or not worker_stopped:
            raise ValueError("Desligue o módulo e pare o worker antes da limpeza.")
        for path in files:
            path.unlink(missing_ok=True)
        db.execute(delete(PreviewAdjustment))
        db.commit()
        report["deleted"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker-stopped", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(cleanup(db, execute=args.execute, worker_stopped=args.worker_stopped)))


if __name__ == "__main__":
    main()
