from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import RawDevelopmentSettings
from app.main import app, db_session


def test_raw_development_settings_endpoints_require_admin_session():
    engine = create_engine("sqlite://")
    RawDevelopmentSettings.__table__.create(engine)

    def temporary_session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[db_session] = temporary_session
    try:
        client = TestClient(app)
        assert client.get("/admin/settings/raw-development").status_code == 403
        assert client.get("/admin/settings/raw-development/capabilities").status_code == 403
        assert client.patch(
            "/admin/settings/raw-development",
            json={"enabled": True, "selected_engine": "lightcraft"},
        ).status_code == 403
        assert client.post("/admin/settings/raw-development/release-check").status_code == 403
        source_path = f"/admin/photo-assets/{uuid4()}/source"
        assert client.put(
            source_path,
            content=b"II*\x00raw-source",
            headers={"content-type": "application/octet-stream"},
        ).status_code == 403
        assert client.get(source_path).status_code in {404, 405}
    finally:
        app.dependency_overrides.pop(db_session, None)
        RawDevelopmentSettings.__table__.drop(engine)
        engine.dispose()
