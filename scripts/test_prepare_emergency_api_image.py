"""The emergency image may change four distributions and no other package."""
import unittest

from prepare_emergency_api_image import PINS, validate_packages


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.before = {"python": "3.13.16", "packages": {"aiohttp": "3.14.3", "multidict": "6.8.0",
                       "urllib3": "2.7.0", "yarl": "1.24.5", "fastapi": "0.142.2"}}
        self.after = {"python": "3.13.16", "packages": {**self.before["packages"], **PINS}}

    def test_four_pins_only(self):
        validate_packages(self.before, self.after)

    def test_other_distribution_or_python_drift_is_refused(self):
        for key, value in (("fastapi", "0.999"), ("extra-package", "1.0"), ("aiohttp", "3.14.3")):
            with self.subTest(key=key):
                altered = {**self.after, "packages": {**self.after["packages"], key: value}}
                with self.assertRaises(ValueError):
                    validate_packages(self.before, altered)
        with self.assertRaises(ValueError):
            validate_packages(self.before, {**self.after, "python": "3.13.17"})

    def test_removed_distribution_is_refused(self):
        del self.after["packages"]["fastapi"]
        with self.assertRaises(ValueError):
            validate_packages(self.before, self.after)


if __name__ == "__main__":
    unittest.main()
