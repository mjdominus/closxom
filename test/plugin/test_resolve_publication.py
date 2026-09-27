import logging
from datetime import datetime, timezone

from closxom.plugin.resolve_publication import ResolvePublicationPlugin
from closxom.skrap import ArticleSkrap

NOW = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_article(db, name, published_raw=None):
    meta = {}
    if published_raw is not None:
        meta['published_raw'] = published_raw
    article = ArticleSkrap(name=name, owner="process-meta", meta=meta)
    db.save_skrap(article, owner="process-meta")
    return article


def _get_article(db, name):
    return db.find_skrap_by_name("process-meta", name)


def test_no_published_raw_is_unconditionally_unpublished(skrapdb):
    _make_article(skrapdb, "foo.blog")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published'] == 0
    assert 'pubdate' not in article.meta


def test_past_published_raw_is_published(skrapdb):
    _make_article(skrapdb, "foo.blog", published_raw="2027-01-01")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published'] == 1
    assert article.meta['pubdate'] == "2027-01-01T17:00:00+00:00"


def test_future_published_raw_is_not_yet_published(skrapdb):
    _make_article(skrapdb, "foo.blog", published_raw="2027-12-31")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published'] == 0
    assert article.meta['pubdate'] == "2027-12-31T17:00:00+00:00"


def test_future_pubdate_flips_to_published_on_a_later_build(skrapdb):
    _make_article(skrapdb, "foo.blog", published_raw="2027-06-15")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()
    assert _get_article(skrapdb, "foo.blog").meta['published'] == 0

    later = datetime(2027, 7, 1, tzinfo=timezone.utc)
    ResolvePublicationPlugin(skrapdb, {}, now=later).run()
    assert _get_article(skrapdb, "foo.blog").meta['published'] == 1


def test_malformed_published_raw_is_treated_as_absent(skrapdb, caplog):
    _make_article(skrapdb, "foo.blog", published_raw="not a date")

    with caplog.at_level(logging.ERROR, logger="closxom.plugin.resolve-publication"):
        ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published'] == 0
    assert 'pubdate' not in article.meta
    assert "not a date" in caplog.text


def test_deleting_published_raw_unpublishes_a_previously_published_article(skrapdb):
    article = _make_article(skrapdb, "foo.blog", published_raw="2027-01-01")
    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()
    assert _get_article(skrapdb, "foo.blog").meta['published'] == 1

    # Simulate the author deleting the published: line: process_meta would
    # remove published_raw from meta on its next run.
    article = _get_article(skrapdb, "foo.blog")
    del article.meta['published_raw']
    skrapdb.save_skrap(article, owner="process-meta")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['published'] == 0
    assert 'pubdate' not in article.meta


def test_does_not_resave_when_nothing_changed(skrapdb):
    _make_article(skrapdb, "foo.blog", published_raw="2027-01-01")

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()
    first_last_updated = _get_article(skrapdb, "foo.blog").last_updated

    ResolvePublicationPlugin(skrapdb, {}, now=NOW).run()
    second_last_updated = _get_article(skrapdb, "foo.blog").last_updated

    assert first_last_updated == second_last_updated


def test_uses_configured_timezone(skrapdb):
    _make_article(skrapdb, "foo.blog", published_raw="2027-01-01")

    ResolvePublicationPlugin(skrapdb, {'timezone': 'UTC'}, now=NOW).run()

    article = _get_article(skrapdb, "foo.blog")
    assert article.meta['pubdate'] == "2027-01-01T12:00:00+00:00"
