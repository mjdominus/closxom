from cloxsom.plugins.readfiles import ReadFilesPlugin
from cloxsom.skrap import FileSkrap


def _save_file_skrap(db, name="foo.blog", content="original", meta=None):
    fs = db.find_skrap_by_name("scanfiles", name)
    if fs is None:
        fs = FileSkrap(name=name, owner="scanfiles", meta=dict(meta or {}))
    elif meta:
        fs.meta.update(meta)
    fs.content = content
    db.save_skrap(fs)
    return fs


def _article(db, name="foo.blog"):
    return db.find_skrap_by_name("readfiles", name)


def test_creates_article_from_file_skrap(skrapdb):
    _save_file_skrap(skrapdb, content="hello body")

    ReadFilesPlugin(skrapdb, {}).run()

    art = _article(skrapdb)
    assert art is not None
    assert art.owner == "readfiles"
    assert art.content == "hello body"


def test_unchanged_file_skrap_is_not_resaved(skrapdb):
    _save_file_skrap(skrapdb, content="hello")
    ReadFilesPlugin(skrapdb, {}).run()
    first = _article(skrapdb).last_updated

    ReadFilesPlugin(skrapdb, {}).run()

    assert _article(skrapdb).last_updated == first


def test_changed_content_updates_article(skrapdb):
    _save_file_skrap(skrapdb, content="v1")
    ReadFilesPlugin(skrapdb, {}).run()

    _save_file_skrap(skrapdb, content="v2")
    ReadFilesPlugin(skrapdb, {}).run()

    assert _article(skrapdb).content == "v2"


def test_stale_file_skrap_with_equal_content_is_not_resaved(skrapdb):
    _save_file_skrap(skrapdb, content="same")
    ReadFilesPlugin(skrapdb, {}).run()
    first = _article(skrapdb).last_updated

    # scanfiles re-saved the FileSkrap (newer last_updated) but the content
    # did not actually change - a benign mtime touch. The base run() will
    # call build_target because the dependency looks stale; build_target
    # must notice the content is equal and not resave the article.
    _save_file_skrap(skrapdb, content="same")
    ReadFilesPlugin(skrapdb, {}).run()

    assert _article(skrapdb).last_updated == first


def test_file_skrap_with_no_content_is_skipped(skrapdb):
    fs = FileSkrap(name="foo.blog", owner="scanfiles", meta={})
    fs.content = None
    skrapdb.save_skrap(fs)

    ReadFilesPlugin(skrapdb, {}).run()

    assert _article(skrapdb) is None


def test_explicit_target_list_limits_which_articles_are_built(skrapdb):
    _save_file_skrap(skrapdb, name="a.blog", content="aaa")
    _save_file_skrap(skrapdb, name="b.blog", content="bbb")

    ReadFilesPlugin(skrapdb, {}).run(["a.blog"])

    assert _article(skrapdb, "a.blog") is not None
    assert _article(skrapdb, "b.blog") is None
