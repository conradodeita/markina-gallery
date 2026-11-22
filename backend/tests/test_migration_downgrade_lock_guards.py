"""Guards estáticos para downgrades Alembic que preservam estado."""

import ast
import re
from pathlib import Path

MIGRATIONS = Path(__file__).parents[1] / "migrations" / "versions"


def _guarded_downgrades():
    for path in sorted(MIGRATIONS.glob("2026*_*.py")):
        revision_match = re.search(r"_(\d{4})_", path.name)
        if not revision_match:
            continue
        revision = int(revision_match.group(1))
        if not 94 <= revision <= 126:
            continue
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        downgrade = next(
            (
                node for node in module.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "downgrade"
            ),
            None,
        )
        if downgrade is None:
            continue
        body = "\n".join(
            source.splitlines()[downgrade.lineno - 1:downgrade.end_lineno]
        )
        if re.search(r"\bSELECT\s+EXISTS\b", body, re.IGNORECASE):
            yield path.name, body


def test_data_preserving_downgrades_lock_before_the_first_guard():
    guarded = list(_guarded_downgrades())
    assert guarded

    for name, body in guarded:
        lock = re.search(r"\bLOCK\s+TABLE\b", body, re.IGNORECASE)
        guard = re.search(r"\bSELECT\s+EXISTS\b", body, re.IGNORECASE)
        assert lock is not None, f"{name}: guard sem LOCK TABLE"
        assert guard is not None and lock.start() < guard.start(), (
            f"{name}: o lock deve preceder o primeiro guard"
        )
        lock_statement = body[lock.start():guard.start()]
        assert re.search(
            r"IN\s+ACCESS\s+EXCLUSIVE\s+MODE\s+NOWAIT",
            lock_statement,
            re.IGNORECASE,
        ), f"{name}: lock precisa ser ACCESS EXCLUSIVE NOWAIT"
