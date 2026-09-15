"""genblog and run-plugin must reject an unknown --timezone before doing
anything else (no DB created), rather than failing later downstream."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_script(name):
    path = REPO_ROOT / name
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_file_location(name, path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("script_name, extra_args", [
    ("genblog", ["--input", "/nonexistent"]),
    ("run-plugin", ["scanfiles"]),
])
def test_bad_timezone_exits_nonzero_before_touching_db(
        monkeypatch, tmp_path, script_name, extra_args):
    module = _load_script(script_name)
    db_path = tmp_path / "test.db"
    argv = [script_name, *extra_args, "--db", str(db_path), "--timezone", "Not/AZone"]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() != 0
    assert not db_path.exists()
