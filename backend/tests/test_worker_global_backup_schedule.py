from __future__ import annotations

import ast
from pathlib import Path


def test_global_backup_is_the_last_low_priority_worker_action():
    source = Path(__file__).resolve().parents[1] / "app" / "worker.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    run_cycle = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_cycle"
    )
    returns = [node for node in ast.walk(run_cycle) if isinstance(node, ast.Return)]

    assert len(returns) == 1
    expression = returns[0].value
    assert isinstance(expression, ast.BoolOp)
    assert isinstance(expression.op, ast.Or)
    assert isinstance(expression.values[-1], ast.Call)
    assert isinstance(expression.values[-1].func, ast.Name)
    assert expression.values[-1].func.id == "process_scheduled_global_postgresql_backup"
    assert all(
        not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "process_scheduled_global_postgresql_backup"
        )
        for value in expression.values[:-1]
    )
