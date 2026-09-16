from datetime import datetime, timezone


def test_record_and_get_latest_build_time(skrapdb):
    now = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    skrapdb.record_build_time(now)
    assert skrapdb.get_latest_build_time() == now


def test_get_latest_build_time_returns_none_when_empty(skrapdb):
    assert skrapdb.get_latest_build_time() is None


def test_get_latest_build_time_returns_the_most_recent(skrapdb):
    first = datetime(2027, 1, 1, tzinfo=timezone.utc)
    second = datetime(2027, 6, 1, tzinfo=timezone.utc)
    skrapdb.record_build_time(first)
    skrapdb.record_build_time(second)
    assert skrapdb.get_latest_build_time() == second
