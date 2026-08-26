"""Worker isolado para os jobs de mídia privados da Markina Gallery."""

import time

from sqlalchemy import select

from app.auth import MediaJob, PhotoAsset, SessionLocal, now
from app.media import generate_derivatives


def process_next_media_job() -> bool:
    """Reserva e executa um job pendente, retornando se havia trabalho."""
    with SessionLocal() as db:
        job = db.scalar(
            select(MediaJob)
            .where(MediaJob.kind == "generate_derivatives", MediaJob.status == "queued")
            .order_by(MediaJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not job:
            return False
        job.status = "processing"
        job.attempts += 1
        job.updated_at = now()
        db.commit()

        photo = db.get(PhotoAsset, job.photo_asset_id)
        if not photo:
            job.status = "failed"
            job.last_error = "Foto de origem não encontrada."
            job.updated_at = now()
            db.commit()
            return True
        generate_derivatives(db, photo, job)
        return True


def main() -> None:
    print("markina-gallery-worker: pronto para processar mídia privada", flush=True)
    while True:
        if not process_next_media_job():
            time.sleep(2)


if __name__ == "__main__":
    main()
