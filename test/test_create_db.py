from cloxsom.db import DB
import sys

def test_create_db(tmpdir):
    db = DB(tmpdir / "test.db")
    db.create_tables()
    assert(True)

def test_poo(skrapdb):
    assert(True)
