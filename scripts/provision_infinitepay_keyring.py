#!/usr/bin/env python3
"""Preparacao manual do cofre; nao publica, reinicia ou modifica pagamentos."""

import argparse
import base64
import getpass
import hashlib
import json
import os
import secrets
import stat
import subprocess
import sys
from pathlib import Path

STATE = Path("/var/lib/markina-gallery/deploy-state")
KEYRING = STATE / "integration-secrets.env"
BACKUP = STATE / "integration-secrets-backup-20261022.json"
LINK = Path("/opt/markina-gallery/docker/.env.integration-secrets")
KEY_ID = "payments-0086-20261022"
CRYPTO = """
import base64,hashlib,json,sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
v=json.load(sys.stdin)
def decode(s):return base64.b64decode(s,validate=True)
aad=b'pick-your-pic.integration-keyring-backup.v1'
def derive(salt):return hashlib.scrypt(v['password'].encode(),salt=salt,n=131072,r=8,p=1,maxmem=268435456,dklen=32)
if v['mode']=='encrypt':
 import secrets
 salt,nonce=secrets.token_bytes(16),secrets.token_bytes(12)
 key=derive(salt)
 ciphertext=AESGCM(key).encrypt(nonce,v['plaintext'].encode(),aad)
 if AESGCM(key).decrypt(nonce,ciphertext,aad).decode()!=v['plaintext']:raise ValueError('verification failed')
 result={'format':'pick-your-pic.integration-keyring-backup.v1','kdf':'scrypt','n':131072,'r':8,'p':1,
         'salt':base64.b64encode(salt).decode(),'nonce':base64.b64encode(nonce).decode(),'ciphertext':base64.b64encode(ciphertext).decode()}
 print(json.dumps(result))
else:
 b=v['backup']
 if b['format']!='pick-your-pic.integration-keyring-backup.v1':raise ValueError('unknown format')
 if (b['kdf'],b['n'],b['r'],b['p'])!=('scrypt',131072,8,1):raise ValueError('unknown parameters')
 plaintext=AESGCM(derive(decode(b['salt']))).decrypt(decode(b['nonce']),decode(b['ciphertext']),aad).decode()
 if plaintext!=v['expected']:raise ValueError('verification failed')
 print('verified')
"""


def transform(payload, local=False):
    command = (
        [sys.executable, "-c", CRYPTO]
        if local
        else [
            "docker",
            "exec",
            "-i",
            "markina-gallery-api-1",
            "python",
            "-B",
            "-c",
            CRYPTO,
        ]
    )
    p = subprocess.run(
        command, input=json.dumps(payload).encode(), capture_output=True, check=False
    )
    if p.returncode:
        raise RuntimeError("cryptographic operation failed")
    return p.stdout.decode().strip()


def exclusive_write(path, value):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(value)
        f.flush()
        os.fsync(f.fileno())


def self_test():
    password = secrets.token_urlsafe(32)
    plaintext = "synthetic-keyring-only-" + secrets.token_urlsafe(32)
    envelope = json.loads(
        transform(
            {"mode": "encrypt", "password": password, "plaintext": plaintext}, True
        )
    )
    assert (
        transform(
            {
                "mode": "verify",
                "password": password,
                "backup": envelope,
                "expected": plaintext,
            },
            True,
        )
        == "verified"
    )
    for altered in ("password", "ciphertext", "nonce"):
        item = json.loads(json.dumps(envelope))
        wrong = password
        if altered == "password":
            wrong = "wrong-synthetic-only-password"
        else:
            raw = bytearray(base64.b64decode(item[altered]))
            raw[0] ^= 1
            item[altered] = base64.b64encode(raw).decode()
        try:
            transform(
                {
                    "mode": "verify",
                    "password": wrong,
                    "backup": item,
                    "expected": plaintext,
                },
                True,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("tampering not rejected")
    print(
        "self_test=passed correct_restore=1 rejected_wrong_password_or_tampering=3 production_writes=0"
    )


def provision():
    if os.name != "posix" or os.uname().nodename != "clearbudget-vnic":
        raise RuntimeError("unexpected host")
    if (
        STATE.is_symlink()
        or not STATE.is_dir()
        or stat.S_IMODE(STATE.stat().st_mode) != 0o700
    ):
        raise RuntimeError("unsafe state directory")
    if STATE.resolve() != STATE or STATE.stat().st_uid != os.geteuid():
        raise RuntimeError("unexpected directory owner")
    if any(p.exists() or p.is_symlink() for p in (KEYRING, BACKUP, LINK)):
        raise RuntimeError("existing keyring/backup/link; preserve and inspect")
    if any(
        (STATE / name).exists()
        for name in (
            "app-in-flight.sha",
            "web-in-flight.sha",
            "app-rollback-in-flight.sha",
            "web-pending.identity",
        )
    ):
        raise RuntimeError("another release is pending")
    item = json.loads(
        subprocess.check_output(["docker", "inspect", "markina-gallery-api-1"])
    )[0]
    if item["Config"]["Labels"]["com.docker.compose.project"] != "markina-gallery":
        raise RuntimeError("unexpected project")
    values = dict(v.split("=", 1) for v in item["Config"]["Env"] if "=" in v)
    if values.get("APP_ENV") != "staging" or values.get("INTEGRATION_SECRET_KEYS"):
        raise RuntimeError("unexpected environment or existing master key")
    if not sys.stdin.isatty():
        raise RuntimeError("interactive terminal required")
    password = getpass.getpass(
        "Senha do backup (minimo 16 caracteres; entrada oculta): "
    )
    repeated = getpass.getpass("Repita a senha do backup (entrada oculta): ")
    if len(password) < 16 or password != repeated:
        raise RuntimeError("invalid password confirmation")
    key = base64.b64encode(secrets.token_bytes(32)).decode()
    plaintext = (
        "INTEGRATION_SECRET_ENV=staging\nINTEGRATION_SECRET_ACTIVE_KEY_ID="
        + KEY_ID
        + "\nINTEGRATION_SECRET_KEYS="
        + json.dumps({KEY_ID: key}, separators=(",", ":"))
        + "\n"
    )
    envelope = json.loads(
        transform({"mode": "encrypt", "password": password, "plaintext": plaintext})
    )
    # Backup verificado e persistido ANTES do material ativo. Uma falha posterior
    # preserva os arquivos para reconciliacao; nunca apaga ou sobrescreve segredos.
    encoded = (json.dumps(envelope, sort_keys=True, indent=2) + "\n").encode()
    exclusive_write(BACKUP, encoded)
    verified = (
        transform(
            {
                "mode": "verify",
                "password": password,
                "backup": json.loads(BACKUP.read_text()),
                "expected": plaintext,
            }
        )
        == "verified"
    )
    if not verified:
        raise RuntimeError("backup verification failed")
    exclusive_write(KEYRING, plaintext.encode())
    os.symlink(str(KEYRING), str(LINK))
    print(
        "Provisionamento preparado; nenhum container reiniciado e nenhum pagamento criado."
    )
    print("Backup cifrado: " + str(BACKUP))
    print("SHA256 do arquivo cifrado: " + hashlib.sha256(encoded).hexdigest())
    print("Guarde o backup no PC e a senha separadamente. Nao envie a senha pelo chat.")
    print(
        "O cofre somente sera carregado pela API na publicacao coordenada autorizada."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--provision", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        elif args.provision:
            provision()
        else:
            parser.error("select --self-test or --provision")
    except (
        OSError,
        RuntimeError,
        ValueError,
        AssertionError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        EOFError,
        KeyboardInterrupt,
    ):
        print(
            "Operacao nao concluida. Nenhum segredo sera exibido; preserve os arquivos existentes para inspecao.",
            file=sys.stderr,
        )
        sys.exit(1)
