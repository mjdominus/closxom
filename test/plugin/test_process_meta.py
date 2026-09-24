from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.skrap import ArticleSkrap


def _make_article(db, name, content):
    article = ArticleSkrap(name=name, owner="readfiles", content=content)
    db.save_skrap(article)
    return article


def _get_article(db, name):
    return db.find_skrap_by_name("readfiles", name)


def test_published_header_is_stored_as_published_raw(skrapdb):
    _make_article(skrapdb, "foo.blog", "META\ntitle: Foo\npublished: 2027-01-01\n\nBody.")

    ProcessMetaPlugin(skrapdb, {}).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published_raw'] == "2027-01-01"
    assert 'published' not in article.meta


def test_deleting_published_header_clears_published_raw(skrapdb):
    _make_article(skrapdb, "foo.blog", "META\ntitle: Foo\npublished: 2027-01-01\n\nBody.")
    ProcessMetaPlugin(skrapdb, {}).run()
    assert _get_article(skrapdb, "foo.blog").meta['published_raw'] == "2027-01-01"

    article = _get_article(skrapdb, "foo.blog")
    article.content = "META\ntitle: Foo\n\nBody."
    skrapdb.save_skrap(article)

    ProcessMetaPlugin(skrapdb, {}).run()

    assert 'published_raw' not in _get_article(skrapdb, "foo.blog").meta
