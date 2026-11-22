"""The six specialized images consume the fixed Pillow without a model update."""
import unittest
from pathlib import Path

from dependency_release import copied_inputs, parse_compose

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'face-index-worker': 'Dockerfile.face', 'face-search-worker': 'Dockerfile.face',
    'face-maintenance-worker': 'Dockerfile.face',
    'preview-adjustment-worker': 'Dockerfile.preview-adjustment',
}


class PillowPinTests(unittest.TestCase):
    def test_both_declared_pillow_constraints_are_exactly_fixed(self):
        for path in ('backend/requirements.txt', 'scripts/face_spike/requirements.txt'):
            lines = (ROOT / path).read_text(encoding='utf-8').splitlines()
            pins = [line for line in lines if line.lower().startswith('pillow')]
            self.assertEqual(pins, ['Pillow==13.0.0'], path)

    def test_every_specialized_consumer_uses_common_fixed_requirements(self):
        services = {}
        for file in ('docker/docker-compose.yml', 'docker/docker-compose.preview-adjustment.yml'):
            for name, config in parse_compose((ROOT / file).read_text(encoding='utf-8')).items():
                services.setdefault(name, {}).update(config)
        for name, dockerfile in EXPECTED.items():
            with self.subTest(service=name):
                build = services[name]['build']
                self.assertEqual(build['dockerfile'], dockerfile)
                self.assertEqual((ROOT / 'docker' / build['context']).resolve(), (ROOT / 'backend').resolve())
                source = (ROOT / 'backend' / dockerfile).read_text(encoding='utf-8')
                self.assertIn('requirements.txt', copied_inputs(source))
                self.assertIn('-r requirements.txt', source)


if __name__ == '__main__':
    unittest.main()
