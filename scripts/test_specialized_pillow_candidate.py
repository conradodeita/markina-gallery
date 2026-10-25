"""Reject drift and untrusted artifacts before any native preparation."""
import copy
import tempfile
import unittest
from pathlib import Path

from specialized_pillow_candidate import save, select_wheel, validate


def evidence():
    before = {'python': '3.13.16', 'packages': {'pillow': '12.3.0', 'numpy': '2.2.6'},
              'source_sha256': 'source-model-digest', 'pip_check': 0, 'pillow_license': 'MIT-CMU'}
    after = copy.deepcopy(before)
    after['packages']['pillow'] = '13.0.0'
    config = {'Env': ['NO_MODEL_DOWNLOAD=1'], 'Entrypoint': ['python'],
              'Cmd': ['-m', 'app.facial.face_worker'], 'Healthcheck': {'Test': ['CMD', 'true']}}
    base = {'Id': 'sha256:' + 'a' * 64, 'Architecture': 'arm64', 'Config': config,
            'RootFS': {'Layers': ['old-code', 'old-models']}}
    candidate = copy.deepcopy(base)
    candidate['Id'] = 'sha256:' + 'b' * 64
    candidate['RootFS']['Layers'] += ['wheel', 'install-only']
    probe = {'contracts': {}, 'automatic_resize': {}, 'seconds': 1, 'max_rss_kib': 9000}
    for mode in ('RGB', 'L', 'CMYK'):
        for orientation in (1, 3, 6, 8):
            case = mode + '/' + str(orientation)
            probe['contracts'][case] = {
                'decoded': {'size': [193, 257] if orientation in (6, 8) else [257, 193]},
                'horizontal_first': 'exact-horizontal-pixels', 'vertical_first': 'exact-vertical-pixels'}
            probe['automatic_resize'][case] = 'exact-horizontal-pixels'
    candidate_probe = copy.deepcopy(probe)
    for mode in ('RGB', 'L', 'CMYK'):
        for orientation in (6, 8):
            candidate_probe['automatic_resize'][mode + '/' + str(orientation)] = 'exact-vertical-pixels'
    return before, after, base, candidate, probe, candidate_probe


class CandidateTests(unittest.TestCase):
    def test_exact_pillow_only_candidate(self):
        validate(*evidence())

    def test_timing_variation_is_measured_not_a_pixel_change(self):
        args = evidence()
        args[-1]['seconds'] = 1.1
        validate(*args)

    def test_other_package_or_missing_package_rejected(self):
        for packages in ({'pillow': '13.0.0', 'numpy': '2.3.0'}, {'pillow': '13.0.0'}):
            args = evidence()
            args[1]['packages'] = packages
            with self.assertRaisesRegex(ValueError, 'package drift'):
                validate(*args)

    def test_python_or_source_or_license_or_pip_failure_rejected(self):
        for key, value in (('python', '3.13.17'), ('source_sha256', 'different'),
                           ('pillow_license', 'unknown'), ('pip_check', 1)):
            with self.subTest(key=key):
                args = evidence()
                args[1][key] = value
                with self.assertRaises(ValueError):
                    validate(*args)

    def test_wrong_architecture_layers_or_image_rejected(self):
        for field, value in (('Architecture', 'amd64'), ('Id', 'moving:tag'),
                             ('RootFS', {'Layers': ['other-base', 'wheel', 'install']})):
            args = evidence()
            args[3][field] = value
            with self.assertRaises(ValueError):
                validate(*args)

    def test_changed_entrypoint_env_user_healthcheck_rejected(self):
        for field in ('Entrypoint', 'Cmd', 'User', 'WorkingDir', 'Env', 'Healthcheck', 'StopSignal'):
            args = evidence()
            args[3]['Config'][field] = 'changed'
            with self.assertRaisesRegex(ValueError, 'configuration changed'):
                validate(*args)

    def test_unexpected_baseline_rejected(self):
        args = evidence()
        args[0]['packages']['pillow'] = '11.0.0'
        with self.assertRaisesRegex(ValueError, 'baseline Pillow'):
            validate(*args)

    def test_pixel_drift_rejected(self):
        args = evidence()
        args[-1]['contracts']['RGB/6']['horizontal_first'] = 'different'
        with self.assertRaisesRegex(ValueError, 'output drift'):
            validate(*args)

    def test_automatic_resize_must_match_exact_version_specific_oracle(self):
        for position, case in ((4, 'RGB/1'), (5, 'RGB/6')):
            args = evidence()
            args[position]['automatic_resize'][case] = 'unexplained-drift'
            with self.assertRaisesRegex(ValueError, 'resize algorithm'):
                validate(*args)

    def test_receipt_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'receipt.json'
            save(path, {'old': True})
            with self.assertRaises(FileExistsError):
                save(path, {'new': True})
            self.assertIn('old', path.read_text())


class WheelTests(unittest.TestCase):
    def metadata(self):
        return {'info': {'version': '13.0.0'}, 'urls': [{
            'filename': 'pillow-13.0.0-cp313-cp313-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl',
            'packagetype': 'bdist_wheel', 'url': 'https://files.pythonhosted.org/packages/wheel.whl',
            'digests': {'sha256': 'c' * 64}, 'size': 123456, 'yanked': False}]}

    def test_exact_official_wheel(self):
        self.assertEqual(select_wheel(self.metadata())['size'], 123456)

    def test_reject_wrong_origin_checksum_size_yanked(self):
        for key, value in (('url', 'https://evil.invalid/wheel.whl'), ('size', 100_000_000),
                           ('digests', {'sha256': 'bad'}), ('yanked', True)):
            metadata = self.metadata()
            metadata['urls'][0][key] = value
            with self.assertRaises(ValueError):
                select_wheel(metadata)

    def test_reject_ambiguous_or_missing_abi(self):
        for urls in ([], self.metadata()['urls'] * 2):
            metadata = self.metadata()
            metadata['urls'] = urls
            with self.assertRaises(ValueError):
                select_wheel(metadata)


if __name__ == '__main__':
    unittest.main()
