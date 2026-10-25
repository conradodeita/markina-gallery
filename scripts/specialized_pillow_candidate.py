"""Prepare six immutable Pillow-only candidates. Does not replace active services.

Run on the native ARM64 host. Receipts contain image/package proofs, never env or
customer data. There is deliberately no deploy/migration/cleanup command here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SERVICES = (
    'face-index-worker', 'face-search-worker', 'face-maintenance-worker',
    'face-gemma-index-worker', 'preview-adjustment-worker', 'raw-development-worker',
)
VERSION = '13.0.0'
PROJECT = 'markina-gallery'
MAX_WHEEL = 32 * 1024 * 1024
METADATA = r'''
import hashlib,importlib.metadata as m,json,platform,subprocess
from pathlib import Path
packages={}
for d in m.distributions():
    name=d.metadata['Name'].lower().replace('_','-')
    if name in packages: raise ValueError('duplicate distribution')
    packages[name]=d.version
source=hashlib.sha256()
protected=(Path('/app/app'),Path('/app/facial-assets'),Path('/app/migrations'),
 Path('/opt/markina-face-models'),Path('/opt/markina-embeddinggemma-2'))
paths=sorted([p for root in protected for p in root.rglob('*')]+
 list(Path('/app').glob('*requirements*.txt'))+[Path('/app/alembic.ini')])
for p in paths:
    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):
        source.update(str(p).encode()+b'\0')
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):source.update(block)
        source.update(b'\0')
check=subprocess.run(['python','-m','pip','check'],capture_output=True,text=True)
print(json.dumps({'python':platform.python_version(),'packages':packages,
 'source_sha256':source.hexdigest(),'pip_check':check.returncode,
 'pillow_license':m.metadata('Pillow').get('License-Expression')}))
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def output(*args, **kwargs):
    return subprocess.check_output(list(args), text=True, timeout=900, **kwargs).strip()


def image_id(value):
    require(isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value), 'invalid image ID')
    return value


def validate(before, after, base, candidate, baseline_probe, candidate_probe):
    image_id(base['Id'])
    image_id(candidate['Id'])
    require(base['Architecture'] == candidate['Architecture'] == 'arm64', 'not native ARM64')
    require(candidate['RootFS']['Layers'][:-2] == base['RootFS']['Layers'], 'base layers changed')
    for field in ('Entrypoint', 'Cmd', 'User', 'WorkingDir', 'Env', 'Healthcheck', 'StopSignal'):
        require(base['Config'].get(field) == candidate['Config'].get(field), 'image configuration changed: ' + field)
    require(before['python'] == after['python'] and before['python'].startswith('3.13.'), 'Python changed')
    require(before['packages'].get('pillow') == '12.3.0', 'unexpected baseline Pillow')
    require(after['packages'] == dict(before['packages'], pillow=VERSION), 'unrelated package drift')
    require(after['source_sha256'] == before['source_sha256'], 'application/model source changed')
    require(before['pip_check'] == after['pip_check'] == 0, 'pip check failed')
    require(after['pillow_license'] == 'MIT-CMU', 'unexpected Pillow license')
    require(baseline_probe['contracts'] == candidate_probe['contracts'], 'synthetic output drift')
    # Pillow13 Resample.c deliberately chooses the vertical pass first when
    # height reduction exceeds twice width reduction. Compare both explicit
    # separable oracles bit-for-bit across versions, then require each default
    # to match its documented implementation exactly; no pixel tolerance.
    for mode in ('RGB', 'L', 'CMYK'):
        for orientation in (1, 3, 6, 8):
            case = mode + '/' + str(orientation)
            record = baseline_probe['contracts'][case]
            width, height = record['decoded']['size']
            vertical_first = height - 96 > 0 and height - 96 > (width - 128) * 2
            require(baseline_probe['automatic_resize'][case] == record['horizontal_first'],
                    'unexpected Pillow12 resize algorithm')
            expected = record['vertical_first' if vertical_first else 'horizontal_first']
            require(candidate_probe['automatic_resize'][case] == expected,
                    'unexpected Pillow13 resize algorithm')


def isolated(image, code):
    return output('docker', 'run', '--rm', '--pull=never', '--platform', 'linux/arm64',
                  '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                  '--security-opt', 'no-new-privileges', '--memory', '1g', '--cpus', '1',
                  '--pids-limit', '128', '--tmpfs', '/tmp:rw,nosuid,size=256m',
                  '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'APP_ENV=development',
                  '-e', 'DATABASE_URL=sqlite:////tmp/synthetic.sqlite',
                  '-e', 'GALLERY_CAPABILITY_SIGNING_KEY=synthetic-only-capability-key-32-bytes-long',
                  '--entrypoint', 'python', image_id(image), '-B', '-c', code)


def select_wheel(metadata):
    require(metadata['info']['version'] == VERSION, 'wrong PyPI version')
    wheels = [item for item in metadata['urls']
              if re.fullmatch(r'pillow-13\.0\.0-cp313-cp313-manylinux_[A-Za-z0-9_.]+_aarch64\.whl', item['filename'])
              and item['packagetype'] == 'bdist_wheel' and not item.get('yanked')]
    require(len(wheels) == 1, 'ambiguous/missing ARM64 CPython313 wheel')
    wheel = wheels[0]
    url = urlparse(wheel['url'])
    require(url.scheme == 'https' and url.hostname == 'files.pythonhosted.org', 'unofficial wheel origin')
    require(re.fullmatch('[0-9a-f]{64}', wheel['digests']['sha256']), 'invalid wheel checksum')
    require(0 < wheel['size'] <= MAX_WHEEL, 'oversized wheel')
    return wheel


def active():
    result = {}
    for service in SERVICES:
        identifiers = output('docker', 'ps', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                             '--filter', 'label=com.docker.compose.service=' + service, '--format', '{{.ID}}').splitlines()
        require(len(identifiers) == 1, 'missing/duplicate active service: ' + service)
        item = json.loads(output('docker', 'inspect', identifiers[0]))[0]
        require(item['State']['Status'] == 'running' and item['State'].get('Health', {}).get('Status') == 'healthy',
                'unhealthy service: ' + service)
        result[service] = {'container_id': item['Id'], 'image_id': image_id(item['Image']),
                           'started_at': item['State']['StartedAt']}
    return result


def sync_directory(path):
    if os.name != 'nt':
        descriptor = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def save(path, data):
    # Exclusive creation: retries never overwrite a previous evidence receipt.
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def prepare(receipt):
    require(platform.machine() in ('aarch64', 'arm64'), 'native ARM64 host required')
    require(not receipt.exists() and receipt.parent.is_dir(), 'receipt exists or parent missing')
    inventory = active()
    with urllib.request.urlopen('https://pypi.org/pypi/Pillow/13.0.0/json', timeout=30) as response:
        metadata = json.load(response)
    wheel = select_wheel(metadata)
    probe_code = Path(__file__).with_name('specialized_pillow_probe.py').read_text(encoding='utf-8')
    result = {'schema_version': 1, 'prepared_at': datetime.now(timezone.utc).isoformat(),
              'project': PROJECT, 'publication_authorized': False, 'active_before': inventory,
              'wheel': {key: wheel[key] for key in ('filename', 'url', 'size', 'digests')}, 'services': {}}
    # Temporary directory contains only the public wheel and fixed Dockerfile.
    with tempfile.TemporaryDirectory(prefix='pyp-pillow-build-') as temporary:
        root = Path(temporary)
        with urllib.request.urlopen(wheel['url'], timeout=45) as response:
            require(urlparse(response.url).hostname == 'files.pythonhosted.org', 'wheel redirect rejected')
            binary = response.read(MAX_WHEEL + 1)
        require(len(binary) == wheel['size'], 'wheel size mismatch')
        require(hashlib.sha256(binary).hexdigest() == wheel['digests']['sha256'], 'wheel checksum mismatch')
        (root / wheel['filename']).write_bytes(binary)
        for service, running in inventory.items():
            previous = running['image_id']
            base = json.loads(output('docker', 'image', 'inspect', previous))[0]
            before = json.loads(isolated(previous, METADATA))
            baseline_probe = json.loads(isolated(previous, probe_code))
            # BuildKit treats a bare sha256 ID as a remote repository. Give only
            # this exact local ID a private content-addressed alias, never an active tag.
            alias = 'markina-pillow-source:' + previous.split(':')[1]
            subprocess.run(['docker', 'tag', previous, alias], check=True, timeout=30)
            require(json.loads(output('docker', 'image', 'inspect', alias))[0]['Id'] == previous,
                    'local base alias drift')
            dockerfile = ('FROM ' + alias + '\nCOPY ' + wheel['filename'] + ' /tmp/' + wheel['filename'] + '\n'
                          'RUN python -m pip install --no-index --no-deps --no-cache-dir /tmp/' + wheel['filename']
                          + ' && rm /tmp/' + wheel['filename'] + '\n')
            (root / 'Dockerfile').write_text(dockerfile, encoding='utf-8')
            iid = root / (service + '.iid')
            subprocess.run(['docker', 'build', '--pull=false', '--network=none', '--iidfile', str(iid),
                            '--label', 'com.pickyourpic.pillow-candidate=13.0.0', str(root)],
                           check=True, timeout=600, stdout=sys.stderr, stderr=sys.stderr)
            candidate_id = image_id(iid.read_text().strip())
            candidate = json.loads(output('docker', 'image', 'inspect', candidate_id))[0]
            after = json.loads(isolated(candidate_id, METADATA))
            candidate_probe = json.loads(isolated(candidate_id, probe_code))
            validate(before, after, base, candidate, baseline_probe, candidate_probe)
            result['services'][service] = {'previous_image': previous, 'candidate_image': candidate_id,
                                           'before': before, 'after': after,
                                           'baseline_probe': baseline_probe, 'candidate_probe': candidate_probe}
            # Keep completed evidence even if a later consumer fails.
            save(receipt.with_name(receipt.name + '.' + service), result['services'][service])
            print(service + '=validated', flush=True)
    require(active() == inventory, 'active service changed during preparation')
    result['active_unchanged'] = True
    save(receipt, result)
    print('prepared=6 active_services_unchanged=true publication=false', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    prepare(parser.parse_args().receipt)
