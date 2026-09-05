
import cloxsom

test_type = "test"

def test_create_bare_skrap():
    skrap = cloxsom.skrap.TestSkrap("test item", "tests")
    assert skrap.last_updated is not None
    assert skrap.meta is not None
    assert skrap.type == test_type

def test_create_fails():
    assert(True)

def test_create_skrap_with_meta():
    skrap = cloxsom.skrap.TestSkrap("test item", "tests", { "key": "value" })
    assert skrap.meta["key"] == "value"
