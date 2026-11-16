"""O runner visual não pode apontar para banco persistente ou origem pública."""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
path = Path(__file__).with_name("local_tenant_closure_demo.py")
spec = importlib.util.spec_from_file_location("closure_demo", path)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_visual_demo_rejects_real_targets_and_missing_credentials():
    environment = {
        "APP_ENV": "development", "PUBLIC_APP_ORIGIN": demo.ORIGIN,
        "DATABASE_URL": "postgresql+psycopg://synthetic:synthetic@127.0.0.1:15478/pyp_closure_ui",
        "PYP_CLOSURE_DEMO_PASSWORD": "synthetic", "PYP_CLOSURE_DEMO_TOTP": "synthetic",
    }
    assert demo.validate_target(environment) == environment["DATABASE_URL"]
    for field, value in (
        ("APP_ENV", "production"), ("PUBLIC_APP_ORIGIN", "https://pickyourpic.com.br"),
        ("DATABASE_URL", "postgresql://synthetic:synthetic@127.0.0.1:5432/pyp_closure_ui"),
        ("DATABASE_URL", "postgresql://synthetic:synthetic@132.145.193.169:15478/pyp_closure_ui"),
        ("DATABASE_URL", "postgresql://synthetic:synthetic@127.0.0.1:15478/markina_gallery"),
        ("DATABASE_URL", "postgresql://synthetic:synthetic@127.0.0.1:15478/pyp_closure_ui?hostaddr=132.145.193.169"),
        ("PGHOSTADDR", "132.145.193.169"),
        ("PGSERVICE", "production"),
        ("PYP_CLOSURE_DEMO_PASSWORD", ""), ("PYP_CLOSURE_DEMO_TOTP", ""),
    ):
        with pytest.raises(ValueError):
            demo.validate_target({**environment, field: value})
