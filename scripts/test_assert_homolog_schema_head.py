import tempfile
import unittest
from pathlib import Path

from assert_homolog_schema_head import migration_heads, validate_database_revision


class AlembicHeadValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def migration(self, filename: str, revision: str, down_revision: str | None) -> None:
        self.directory.joinpath(filename).write_text(
            f"revision = {revision!r}\ndown_revision = {down_revision!r}\n", encoding="utf-8"
        )

    def test_accepts_database_at_single_head(self) -> None:
        self.migration("001.py", "one", None)
        self.migration("002.py", "two", "one")
        self.assertEqual(validate_database_revision(self.directory, "two"), "two")

    def test_rejects_database_behind_head(self) -> None:
        self.migration("001.py", "one", None)
        self.migration("002.py", "two", "one")
        with self.assertRaisesRegex(ValueError, "schema incompatível"):
            validate_database_revision(self.directory, "one")

    def test_rejects_multiple_heads(self) -> None:
        self.migration("001.py", "one", None)
        self.migration("002.py", "two", None)
        self.assertEqual(len(migration_heads(self.directory)), 2)
        with self.assertRaisesRegex(ValueError, "único head"):
            validate_database_revision(self.directory, "one")

    def test_rejects_missing_ancestor(self) -> None:
        self.migration("001.py", "two", "missing")
        with self.assertRaisesRegex(ValueError, "ancestrais.*ausentes"):
            migration_heads(self.directory)


if __name__ == "__main__":
    unittest.main()
