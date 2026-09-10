from closxom.plugin.base import Plugin
from closxom.skrap import FileSkrap


class _P(Plugin):
    @classmethod
    def name(cls):
        return "updater"


def _fresh_skrap(db, **meta):
    s = FileSkrap(name="s", owner="updater", meta=dict(meta))
    db.save_skrap(s)
    return db.find_skrap_by_name("updater", "s")


def test_update_returns_true_and_saves_on_change(skrapdb):
    s = _fresh_skrap(skrapdb)
    plugin = _P(skrapdb, {})

    assert plugin.update_skrap_meta(s, published=False) is True
    assert skrapdb.find_skrap_by_name("updater", "s").meta['published'] == 0


def test_update_returns_false_and_does_not_save_when_unchanged(skrapdb):
    s = _fresh_skrap(skrapdb, published=False)
    plugin = _P(skrapdb, {})
    before = skrapdb.find_skrap_by_name("updater", "s").last_updated

    assert plugin.update_skrap_meta(s, published=False) is False
    assert skrapdb.find_skrap_by_name("updater", "s").last_updated == before


def test_update_multiple_keys_saves_once_if_any_changed(skrapdb):
    s = _fresh_skrap(skrapdb, a=1)
    plugin = _P(skrapdb, {})

    assert plugin.update_skrap_meta(s, a=1, b=2) is True
    reloaded = skrapdb.find_skrap_by_name("updater", "s")
    assert reloaded.meta['a'] == 1
    assert reloaded.meta['b'] == 2


def test_defaults_sets_absent_key_and_saves(skrapdb):
    s = _fresh_skrap(skrapdb)
    plugin = _P(skrapdb, {})

    assert plugin.set_skrap_meta_defaults(s, published=True) is True
    assert skrapdb.find_skrap_by_name("updater", "s").meta['published'] == 1


def test_defaults_leaves_present_key_untouched(skrapdb):
    s = _fresh_skrap(skrapdb, published=False)
    plugin = _P(skrapdb, {})
    before = skrapdb.find_skrap_by_name("updater", "s").last_updated

    assert plugin.set_skrap_meta_defaults(s, published=True) is False
    reloaded = skrapdb.find_skrap_by_name("updater", "s")
    assert reloaded.meta['published'] == 0
    assert reloaded.last_updated == before
