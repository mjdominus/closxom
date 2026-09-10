
from closxom.db import DB
import pytest
import sys

@pytest.fixture
def skrapdb(tmpdir):
    db = DB(tmpdir / "test.db")
    db.create_tables()
    return db
