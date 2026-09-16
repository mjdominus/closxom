"""genblog and run-plugin must reject a bad --timezone or --time before
doing anything else (no DB created), rather than failing later downstream."""

import pytest

from closxom.app import genblog, run_plugin

MODULES = {
    "genblog": genblog,
    "run-plugin": run_plugin,
}


@pytest.mark.parametrize("script_name, extra_args", [
    ("genblog", ["--input", "/nonexistent"]),
    ("run-plugin", ["scanfiles"]),
])
def test_bad_timezone_exits_nonzero_before_touching_db(tmp_path, script_name, extra_args):
    db_path = tmp_path / "test.db"
    argv = [*extra_args, "--db", str(db_path), "--timezone", "Not/AZone"]

    assert MODULES[script_name].run(argv) != 0
    assert not db_path.exists()


@pytest.mark.parametrize("script_name, extra_args", [
    ("genblog", ["--input", "/nonexistent"]),
    ("run-plugin", ["scanfiles"]),
])
def test_bad_time_exits_nonzero_before_touching_db(tmp_path, script_name, extra_args):
    db_path = tmp_path / "test.db"
    argv = [*extra_args, "--db", str(db_path), "--time", "garbage"]

    assert MODULES[script_name].run(argv) != 0
    assert not db_path.exists()
