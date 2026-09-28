import pytest

from closxom.plugin.base import ArticleFailed
from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.skrap import FileSkrap


def _save_file_skrap(db, name="foo.blog", content="original"):
    fs = db.find_skrap_by_name("scanfiles", name)
    if fs is None:
        fs = FileSkrap(name=name, owner="scanfiles")
    fs.content = content
    db.save_skrap(fs, owner="scanfiles")
    return fs


def _article(db, name="foo.blog"):
    return db.find_skrap_by_name("process-meta", name)


def test_creates_article_from_file_skrap(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nHello body.")

    ProcessMetaPlugin(skrapdb, {}).run()

    art = _article(skrapdb)
    assert art is not None
    assert art.owner == "process-meta"
    assert art.content == "Hello body."
    assert art.meta['title'] == "Foo"


def test_missing_meta_section_fails_article(skrapdb):
    _save_file_skrap(skrapdb, content="Just a plain article.\nMore text.")

    with pytest.raises(ArticleFailed):
        ProcessMetaPlugin(skrapdb, {}).run()


def test_published_header_is_stored_as_published_raw(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\npublished: 2027-01-01\n\nBody.")

    ProcessMetaPlugin(skrapdb, {}).run()

    article = _article(skrapdb)
    assert article.meta['published_raw'] == "2027-01-01"
    assert 'published' not in article.meta


def test_deleting_published_header_clears_published_raw(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\npublished: 2027-01-01\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()
    assert _article(skrapdb).meta['published_raw'] == "2027-01-01"

    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()

    assert 'published_raw' not in _article(skrapdb).meta


def test_meta_section_without_title_fails_article(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntags: x\n\nBody.")

    with pytest.raises(ArticleFailed):
        ProcessMetaPlugin(skrapdb, {}).run()


def test_removing_a_key_from_meta_clears_it(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\ntags: a\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()
    assert _article(skrapdb).meta['tags'] == 'a'

    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()

    assert 'tags' not in _article(skrapdb).meta


def test_body_only_edit_is_saved_even_though_meta_is_unchanged(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nOriginal body.")
    ProcessMetaPlugin(skrapdb, {}).run()

    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nEdited body.")
    ProcessMetaPlugin(skrapdb, {}).run()

    assert _article(skrapdb).content == "Edited body."


def test_unchanged_article_is_not_resaved(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()
    first = _article(skrapdb).last_updated

    ProcessMetaPlugin(skrapdb, {}).run()

    assert _article(skrapdb).last_updated == first


def test_file_resaved_with_unchanged_content_is_not_resaved(skrapdb):
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nSame.")
    ProcessMetaPlugin(skrapdb, {}).run()
    first = _article(skrapdb).last_updated

    # scanfiles re-saved the FileSkrap (newer last_updated) but the content
    # did not actually change - a benign mtime touch. The base run() will
    # call build_target because the dependency looks stale; build_target
    # must notice nothing actually changed and not resave the article.
    _save_file_skrap(skrapdb, content="META\ntitle: Foo\n\nSame.")
    ProcessMetaPlugin(skrapdb, {}).run()

    assert _article(skrapdb).last_updated == first


def test_file_skrap_with_no_content_is_skipped(skrapdb):
    fs = FileSkrap(name="foo.blog", owner="scanfiles")
    fs.content = None
    skrapdb.save_skrap(fs, owner="scanfiles")

    ProcessMetaPlugin(skrapdb, {}).run()

    assert _article(skrapdb) is None


def test_explicit_target_list_limits_which_articles_are_built(skrapdb):
    _save_file_skrap(skrapdb, name="a.blog", content="META\ntitle: A\n\naaa")
    _save_file_skrap(skrapdb, name="b.blog", content="META\ntitle: B\n\nbbb")

    ProcessMetaPlugin(skrapdb, {}).run(["a.blog"])

    assert _article(skrapdb, "a.blog") is not None
    assert _article(skrapdb, "b.blog") is None
