from datetime import datetime, timezone

from closxom.plugin.base import Plugin


class _P(Plugin):
    @classmethod
    def name(cls):
        return "prober"


def test_default_now_is_current_wall_clock(skrapdb):
    before = datetime.now(timezone.utc)
    plugin = _P(skrapdb, {})
    after = datetime.now(timezone.utc)

    assert plugin.now.tzinfo is timezone.utc
    assert before <= plugin.now <= after


def test_explicit_now_is_stored_as_is(skrapdb):
    now = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    plugin = _P(skrapdb, {}, now=now)
    assert plugin.now is now
