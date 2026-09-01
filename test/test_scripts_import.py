"""Import the top-level CLI scripts as modules, without running main(),
to catch syntax errors and bad imports (e.g. a module that no longer
exists) the way `perl -c` catches a bad `use` - without any of the
script's actual behavior running.
"""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = ["genblog", "run-plugin", "create-testdb"]


@pytest.mark.parametrize("script_name", SCRIPTS)
def test_script_imports_cleanly(script_name):
    path = REPO_ROOT / script_name
    loader = SourceFileLoader(script_name, str(path))
    spec = importlib.util.spec_from_file_location(script_name, path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
