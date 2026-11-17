"""Runner interno do NPM descartável, sem rede e com CA/admin sintéticos."""

import hashlib
import json
import os
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from scripts.test_wildcard_certificate_custody import synthetic_bundle, synthetic_ca
from scripts.wildcard_certificate_custody import (
    MARKER,
    CustodyError,
    SyntheticInstaller,
    private_write,
    validate_bundle,
)


def run(installer_factory=SyntheticInstaller, bundle_validator=validate_bundle, installation_error=CustodyError):
    if os.environ.get("PYP_WILDCARD_LAB") != "synthetic-network-none" or os.name != "posix":
        raise RuntimeError("lab_only")
    routes = Path('/proc/net/route').read_text().splitlines()[1:]
    if any(line.split()[1] == '00000000' for line in routes):
        raise RuntimeError("network_not_isolated")
    if json.loads(Path('/app/package.json').read_text())['version'] != '2.15.1':
        raise RuntimeError("wrong_npm_version")
    for _attempt in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:81/api/', timeout=2) as response:
                if response.status == 200 and Path('/data/database.sqlite').is_file():
                    break
        except OSError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('lab_boot_timeout')
    db = sqlite3.connect('file:/data/database.sqlite?mode=ro', uri=True)
    if db.execute('SELECT count(*) FROM proxy_host').fetchone()[0] or db.execute('SELECT count(*) FROM user').fetchone()[0]:
        raise RuntimeError("laboratory_not_empty")

    def api(path, body, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        request = urllib.request.Request('http://127.0.0.1:81/api' + path,
                                         json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)

    api('/users', {'email': 'synthetic@example.test', 'name': 'Synthetic Lab', 'nickname': 'Lab',
                   'auth': {'type': 'password', 'secret': 'SyntheticLabPassword!2026'}})
    token = api('/tokens', {'identity': 'synthetic@example.test', 'secret': 'SyntheticLabPassword!2026'})['token']
    root = Path('/data/pyp-wildcard-certificates')
    root.mkdir(mode=0o700)
    (root / '.pyp-wildcard-lab').write_text(MARKER)
    # Custódia/materialização são ensaiadas em outro container sem NPM.
    # Este consumidor nunca recebe token nem monta o cofre do emissor.
    sentinel = 'synthetic-cloudflare-lab-sentinel'
    ca_key, ca = synthetic_ca()
    trust = ca.public_bytes(serialization.Encoding.PEM)
    installer = installer_factory(root, trust, lambda: None, lambda: None, lambda fp: None)
    first = synthetic_bundle(ca_key, ca)
    first_receipt = installer.install(*first)
    references = {}
    for hostname in ('*.pickyourpic.com.br', 'markina.pickyourpic.com.br', 'pickyourpic.com.br'):
        certificate_path = root / 'current'
        if not hostname.startswith('*.'):
            certificate_path = root / f'reference-{len(references)}'
            certificate_path.mkdir(mode=0o700)
            bundle = synthetic_bundle(ca_key, ca, hostname)
            private_write(certificate_path / 'fullchain.pem', bundle[0])
            private_write(certificate_path / 'privkey.pem', bundle[1])
            leaf = x509.load_pem_x509_certificates(bundle[0])[0]
            references[hostname] = hashlib.sha256(leaf.public_bytes(serialization.Encoding.DER)).hexdigest()
        advanced = (f'listen 443 ssl;\nssl_certificate {certificate_path}/fullchain.pem;\n'
                    f'ssl_certificate_key {certificate_path}/privkey.pem;\nreturn 200 "lab-{hostname}";')
        api('/nginx/proxy-hosts', {'domain_names': [hostname], 'forward_scheme': 'http',
            'forward_host': '127.0.0.1', 'forward_port': 9, 'access_list_id': 0, 'certificate_id': 0,
            'ssl_forced': False, 'caching_enabled': False, 'block_exploits': False,
            'allow_websocket_upgrade': False, 'http2_support': False, 'hsts_enabled': False,
            'hsts_subdomains': False, 'advanced_config': advanced, 'locations': [], 'meta': {}}, token)

    context = ssl.create_default_context(cadata=trust.decode())

    def probe_once(hostname, fingerprint, marker):
        with (socket.create_connection(('127.0.0.1', 443), timeout=2) as raw,
              context.wrap_socket(raw, server_hostname=hostname) as secure):
            actual = hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
            secure.sendall(f'GET / HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'.encode())
            body = b''
            while len(body) < 16384:
                chunk = secure.recv(4096)
                if not chunk:
                    break
                body += chunk
            if actual != fingerprint or b'200 OK' not in body or marker.encode() not in body:
                raise RuntimeError('tls_probe_failed')

    def probe_host(hostname, fingerprint, marker):
        for _attempt in range(40):
            try:
                probe_once(hostname, fingerprint, marker)
                return
            except (OSError, RuntimeError):
                pass
            time.sleep(0.1)
        raise RuntimeError('tls_probe_failed')

    def probe(fingerprint):
        probe_host('brand.pickyourpic.com.br', fingerprint, 'lab-*.pickyourpic.com.br')
        for hostname, expected in references.items():
            probe_host(hostname, expected, f'lab-{hostname}')

    def fixed_command(operation):
        args = {'check': ['nginx', '-t'], 'reload': ['nginx', '-s', 'reload']}[operation]
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    probe(first_receipt['fingerprint'])
    installer.check_config = lambda: fixed_command('check')
    installer.reload_service = lambda: fixed_command('reload')
    installer.probe = probe
    stop = threading.Event()
    continuity = {'checks': 0, 'failures': 0}

    def monitor_references():
        while not stop.is_set():
            for hostname, fingerprint in references.items():
                try:
                    # Sem retries: uma falha observada não pode ser escondida.
                    probe_once(hostname, fingerprint, f'lab-{hostname}')
                    continuity['checks'] += 1
                except (OSError, RuntimeError):
                    continuity['failures'] += 1
            stop.wait(0.02)

    monitor = threading.Thread(target=monitor_references, daemon=True)
    monitor.start()
    try:
        second = synthetic_bundle(ca_key, ca)
        receipt = installer.install(*second)
        assert installer.install(*second)['replayed']
        third = synthetic_bundle(ca_key, ca)
        third_fp = bundle_validator(*third, trust)

        def fail_probe(fp):
            if fp == third_fp:
                raise RuntimeError('synthetic probe failure')
            probe(fp)

        installer.probe = fail_probe
        try:
            installer.install(*third)
            raise AssertionError('failure not exercised')
        except installation_error as error:
            assert str(error) == 'installation_failed'
    finally:
        stop.set()
        monitor.join(timeout=10)
    assert not monitor.is_alive() and continuity['checks'] >= 2 and continuity['failures'] == 0
    probe(receipt['fingerprint'])
    assert not Path('/tmp/pyp-wildcard-vault').exists()
    assert db.execute('SELECT count(*) FROM certificate').fetchone()[0] == 0
    for file in [Path('/data/database.sqlite'), *Path('/data/logs').glob('*.log')]:
        content = file.read_bytes()
        assert sentinel.encode() not in content and b'PRIVATE KEY' not in content
    report = {'result': 'passed', 'npm': '2.15.1', 'tls_verified': True,
                      'renewal_replay': True, 'rollback_verified': True, 'certificate_db_rows': 0,
                      'reference_hosts_unchanged': True, 'issuer_vault_mounted': False,
                      'reference_tls_probes': continuity,
                      'external_network': False}
    Path('/tmp/pyp-wildcard-lab-result.json').write_text(json.dumps(report))
    print(json.dumps(report))


if __name__ == '__main__':
    run()
