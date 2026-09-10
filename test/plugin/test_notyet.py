from closxom.plugins.notyet import NotYetPlugin
from closxom.skrap import ArticleSkrap, FileSkrap


def _make_file_and_article(db, name, has_notyet):
    file_skrap = FileSkrap(name=name, owner="scanfiles", meta={'has_notyet': has_notyet})
    db.save_skrap(file_skrap)
    article = ArticleSkrap(name=name, owner="readfiles")
    db.save_skrap(article)
    return article


def _get_article(db, name):
    return db.find_skrap_by_name("readfiles", name)


def test_notyet_marks_unpublished_when_file_has_notyet(skrapdb):
    _make_file_and_article(skrapdb, "foo.blog", has_notyet=True)

    NotYetPlugin(skrapdb, {}).run()

    # SQLite has no boolean type; published is stored and read back as 0.
    assert _get_article(skrapdb, "foo.blog").meta['published'] == 0


def test_notyet_defaults_to_published_when_no_notyet(skrapdb):
    _make_file_and_article(skrapdb, "foo.blog", has_notyet=False)

    NotYetPlugin(skrapdb, {}).run()

    assert _get_article(skrapdb, "foo.blog").meta['published']


def test_notyet_does_not_resave_already_unpublished_article(skrapdb):
    _make_file_and_article(skrapdb, "foo.blog", has_notyet=True)

    NotYetPlugin(skrapdb, {}).run()
    first_last_updated = _get_article(skrapdb, "foo.blog").last_updated

    NotYetPlugin(skrapdb, {}).run()
    second_last_updated = _get_article(skrapdb, "foo.blog").last_updated

    assert first_last_updated == second_last_updated
