import pytest

from closxom.db import ForeignMetaWrite
from closxom.plugin.base import Plugin
from closxom.skrap import FileSkrap


class _A(Plugin):
    @classmethod
    def name(cls):
        return "plugin-a"


class _B(Plugin):
    @classmethod
    def name(cls):
        return "plugin-b"


def _fresh_skrap(db, owner="creator", **meta):
    s = FileSkrap(name="s", owner=owner, meta=dict(meta))
    db.save_skrap(s, owner=owner)
    return db.find_skrap_by_name(owner, "s")


def test_two_plugins_can_own_different_keys_on_same_skrap(skrapdb):
    s = _fresh_skrap(skrapdb)
    a, b = _A(skrapdb, {}), _B(skrapdb, {})

    a.update_skrap_meta(s, x=1)
    b.update_skrap_meta(skrapdb.find_skrap_by_name("creator", "s"), y=2)

    final = skrapdb.find_skrap_by_name("creator", "s")
    assert final.meta['x'] == 1
    assert final.meta['y'] == 2
    assert skrapdb.meta_keys_owned_by(final, "plugin-a") == {'x'}
    assert skrapdb.meta_keys_owned_by(final, "plugin-b") == {'y'}


def test_mutating_foreign_owned_key_raises(skrapdb):
    s = _fresh_skrap(skrapdb)
    a, b = _A(skrapdb, {}), _B(skrapdb, {})
    a.update_skrap_meta(s, x=1)

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    reloaded.meta['x'] = 999

    with pytest.raises(ForeignMetaWrite):
        b.db.save_skrap(reloaded)

    # the failed save touched nothing
    unchanged = skrapdb.find_skrap_by_name("creator", "s")
    assert unchanged.meta['x'] == 1
    assert skrapdb.meta_keys_owned_by(unchanged, "plugin-a") == {'x'}


def test_deleting_foreign_owned_key_raises(skrapdb):
    s = _fresh_skrap(skrapdb)
    a, b = _A(skrapdb, {}), _B(skrapdb, {})
    a.update_skrap_meta(s, x=1)

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    del reloaded.meta['x']

    with pytest.raises(ForeignMetaWrite):
        b.db.save_skrap(reloaded)

    survivor = skrapdb.find_skrap_by_name("creator", "s")
    assert survivor.meta['x'] == 1
    assert skrapdb.meta_keys_owned_by(survivor, "plugin-a") == {'x'}


def test_row_owner_can_clear_a_foreign_owned_key(skrapdb):
    s = _fresh_skrap(skrapdb)
    b = _B(skrapdb, {})
    b.update_skrap_meta(s, x=1)

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    del reloaded.meta['x']
    skrapdb.save_skrap(reloaded, owner="creator")  # the skrap's own row owner

    survivor = skrapdb.find_skrap_by_name("creator", "s")
    assert 'x' not in survivor.meta


def test_row_owner_cannot_mutate_a_foreign_owned_key(skrapdb):
    s = _fresh_skrap(skrapdb)
    b = _B(skrapdb, {})
    b.update_skrap_meta(s, x=1)

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    reloaded.meta['x'] = 999

    with pytest.raises(ForeignMetaWrite):
        skrapdb.save_skrap(reloaded, owner="creator")

    unchanged = skrapdb.find_skrap_by_name("creator", "s")
    assert unchanged.meta['x'] == 1


def test_reconcile_meta_adds_updates_and_deletes_only_own_keys(skrapdb):
    s = _fresh_skrap(skrapdb)
    a, b = _A(skrapdb, {}), _B(skrapdb, {})
    b.update_skrap_meta(s, foreign=1)

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    assert a.reconcile_meta(reloaded, {'p': 1, 'q': 2}) is True

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    assert a.reconcile_meta(reloaded, {'p': 1}) is True  # drops 'q', keeps 'p'

    final = skrapdb.find_skrap_by_name("creator", "s")
    assert final.meta == {'p': 1, 'foreign': 1}
    assert skrapdb.meta_keys_owned_by(final, "plugin-a") == {'p'}
    assert skrapdb.meta_keys_owned_by(final, "plugin-b") == {'foreign'}


def test_reconcile_meta_returns_false_and_does_not_save_when_unchanged(skrapdb):
    s = _fresh_skrap(skrapdb)
    a = _A(skrapdb, {})
    a.reconcile_meta(s, {'p': 1})
    before = skrapdb.find_skrap_by_name("creator", "s").last_updated

    reloaded = skrapdb.find_skrap_by_name("creator", "s")
    assert a.reconcile_meta(reloaded, {'p': 1}) is False
    assert skrapdb.find_skrap_by_name("creator", "s").last_updated == before
