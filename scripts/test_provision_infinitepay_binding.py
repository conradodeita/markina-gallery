import unittest

from provision_infinitepay_binding import binding


class BindingTests(unittest.TestCase):
    def test_owner_binding_is_explicit_and_raw_value_not_interpolated(self):
        value = binding("11111111-1111-4111-8111-111111111111", "staging", "synthetic-$literal#value")
        self.assertIn('INFINITEPAY_TENANT_BINDINGS={"11111111-1111-4111-8111-111111111111":', value)
        self.assertIn("_CREDENTIAL_ENV=staging\n", value)
        self.assertTrue(value.endswith("_API_KEY=synthetic-$literal#value\n"))

    def test_invalid_keys_and_environment_fail_without_echoing_value(self):
        for key in ("", "secret\nINJECTION=value", " secret", "secret\r", "x" * 513):
            with self.subTest(length=len(key)), self.assertRaisesRegex(ValueError, "invalid key format"):
                binding("11111111-1111-4111-8111-111111111111", "staging", key)
        with self.assertRaises(ValueError):
            binding("11111111-1111-4111-8111-111111111111", "development", "synthetic")


if __name__ == "__main__":
    unittest.main()
