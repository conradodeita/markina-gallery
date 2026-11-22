"""Real Compose 2.35.1 proof, exclusively on a disposable GitHub-hosted runner.

Synthetic resources use a random project; no production access, shared local
daemon, prune, down, or removal of preexisting resources. Runner disposal cleans up.
"""
import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import preview_adjustment_migration_inventory as inventory


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise SystemExit('Only disposable GitHub-hosted runners are allowed')
    project = 'preview-proof-' + uuid.uuid4().hex[:12]
    inventory.PROJECT = project
    environment = {**os.environ, 'COMPOSE_REMOVE_ORPHANS': 'false', 'COMPOSE_IGNORE_ORPHANS': 'true'}

    def run(*args):
        return subprocess.check_output(args, env=environment, text=True, timeout=180).strip()

    def inspect(ident):
        return json.loads(run('docker', 'inspect', ident))[0]

    assert run('docker', 'compose', 'version', '--short').removeprefix('v') == inventory.COMPOSE_VERSION
    run('docker', 'pull', 'alpine:3.21')
    image = run('docker', 'image', 'inspect', '--format', '{{.Id}}', 'alpine:3.21')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'compose.json'
        config = {'services': {name: {'image': image, 'command': ['sleep', '600']}
                               for name in ('api', 'web')},
                  'networks': {'default': {'internal': True}}}
        path.write_text(json.dumps(config))
        command = ['docker', 'compose', '-p', project, '-f', str(path), '--profile', '*']
        run(*command, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'api', 'web')
        # Reproduce the standalone manifest observed after retirement.
        consolidated = Path(directory) / 'active.compose.json'
        consolidated.write_text(run(*command, 'config', '--format', 'json'))
        command = ['docker', 'compose', '-p', project, '-f', str(consolidated), '--profile', '*']
        for name in ('api', 'web'):
            ident = run(*command, 'ps', '-q', name)
            expected = inspect(ident)['Config']['Labels']['com.docker.compose.config-hash']
            assert run(*command, 'config', '--hash', name).split() == [name, expected]
        historic = []
        for index, service in enumerate(['api'] * 3 + ['web'] * 3 + ['migrate', 'legacy-a', 'legacy-b']):
            args = ['docker', 'run', '-d', '--name', project + '-history-' + str(index),
                    '--restart=no', '--network=none', '--label', 'com.docker.compose.project=' + project,
                    '--label', 'com.docker.compose.service=' + service]
            if index >= 6:
                for key, value in [('config-hash', 'a' * 64), ('oneoff', 'False'), ('container-number', '1')]:
                    args += ['--label', 'com.docker.compose.' + key + '=' + value]
            if index >= 7:
                args += ['-v', project + '-volume-' + str(index) + ':/data']
            ident = run(*args, image, 'sh', '-c', 'test ! -d /data || echo synthetic-sentinel > /data/sentinel')
            run('docker', 'wait', ident)
            historic.append(ident)
        # A container from a different synthetic project must also be untouched.
        peer = run('docker', 'run', '-d', '--network=none', '--label',
                   'com.docker.compose.project=' + project + '-peer', image, 'true')
        run('docker', 'wait', peer)
        peer_before = inspect(peer)
        all_ids = run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project).split()
        active, historical = inventory.partition_containers([inspect(i) for i in all_ids])
        assert len(active) == 2 and len(historical) == 9

        def preserved():
            assert [inventory.historical_identity(inspect(i['container_id'])) for i in historical] == historical
            assert inspect(peer) == peer_before

        preserved()
        run(*command, 'run', '--rm', '--no-deps', '-T', 'api', 'true')
        preserved()
        # A candidate configuration forces real replacement, using the production flags.
        config = json.loads(consolidated.read_text())
        for service in config['services'].values():
            service['environment'] = {'SYNTHETIC_CANDIDATE': '1'}
        consolidated.write_text(json.dumps(config))
        run(*command, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'api', 'web')
        preserved()
        for index in (7, 8):
            assert run('docker', 'run', '--rm', '--network=none', '-v',
                       project + '-volume-' + str(index) + ':/data:ro', image,
                       'cat', '/data/sentinel') == 'synthetic-sentinel'
        time.sleep(1)
        preserved()
        print('Compose 2.35.1: nine historical containers, mounted sentinels and peer preserved through run/up')


if __name__ == '__main__':
    main()
