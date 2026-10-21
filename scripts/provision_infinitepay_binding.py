"""Owner-only interactive provisioning; never accepts a secret in arguments."""
from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

TARGET = Path("/opt/markina-gallery/docker/.env.infinitepay-bindings")
OWNER = "conradodeita@gmail.com"


def binding(tenant, environment, key):
    tenant = str(UUID(tenant))
    if environment not in {"staging", "production"}:
        raise ValueError("unexpected environment")
    if not key or key != key.strip() or len(key) > 512 or any(not 32 <= ord(c) <= 126 for c in key):
        raise ValueError("invalid key format")
    alias = "OWNER_" + tenant.replace("-", "")[:12].upper()
    return ("INFINITEPAY_TENANT_BINDINGS=" + json.dumps({tenant: alias}, separators=(",", ":"))
            + "\nINFINITEPAY_BINDING_" + alias + "_CREDENTIAL_ENV=" + environment
            + "\nINFINITEPAY_BINDING_" + alias + "_API_KEY=" + key + "\n")


def main():
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise ValueError("interactive SSH terminal required")
    if TARGET.exists() or TARGET.is_symlink() or TARGET.parent.is_symlink():
        raise ValueError("existing binding or unexpected filesystem; operator review required")
    subprocess.run(["git", "-C", "/opt/markina-gallery", "check-ignore", "-q", str(TARGET)], check=True)
    # Credentials stay inside the container. Query is read-only and prints only
    # the matching active owner UUID and runtime environment.
    query = """
import json,os
from sqlalchemy import text
from app.auth import SessionLocal
with SessionLocal() as db:
    db.execute(text('SET TRANSACTION READ ONLY'))
    rows=db.execute(text('SELECT t.id,t.status FROM tenant t JOIN tenant_admin ta ON ta.tenant_id=t.id JOIN admin_user a ON a.id=ta.admin_user_id WHERE a.email=:email AND ta.active=true'),{'email':'conradodeita@gmail.com'}).all()
    assert len(rows)==1 and rows[0].status=='active'
    print(json.dumps({'tenant':str(rows[0].id),'environment':os.environ['APP_ENV']}))
"""
    info = json.loads(subprocess.check_output(["docker", "exec", "-e", "PYTHONDONTWRITEBYTECODE=1",
                      "markina-gallery-api-1", "python", "-B", "-c", query], text=True))
    print("Conta verificada:", OWNER, "| tenant:", info["tenant"], "| ambiente:", info["environment"])
    key = getpass.getpass("API Key InfinitePay (entrada oculta): ").strip()
    if key != getpass.getpass("Repita a API Key (entrada oculta): ").strip():
        raise ValueError("confirmation differs")
    value = binding(info["tenant"], info["environment"], key)
    descriptor = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        destination.write(value)
        destination.flush()
        os.fsync(destination.fileno())
    print("Binding gravado com permissão 0600. Nenhum checkout ou pagamento foi criado.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, EOFError, KeyboardInterrupt) as error:
        reason = {
            "confirmation differs": "As duas entradas não coincidem.",
            "invalid key format": "Formato recusado: deve ser texto de uma linha, até 512 caracteres, sem controles.",
            "unexpected environment": "Ambiente não autorizado.",
        }.get(str(error), "Verificação de terminal, conta ou arquivo não concluída.") if isinstance(error, ValueError) else "Falha de acesso ao arquivo, consulta ou entrada interrompida."
        print("Provisionamento não concluído. " + reason + " Nenhum segredo foi exibido.", file=sys.stderr)
        raise SystemExit(1) from None
