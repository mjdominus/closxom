import pytest

from closxom.plugin.base import ArticleFailed
from closxom.plugin.formatter import FormatterPlugin
from closxom.skrap import ArticleSkrap


def _make_article(db, name, content, formatter=None):
    meta = {}
    if formatter is not None:
        meta['formatter'] = formatter
    article = ArticleSkrap(name=name, owner="process-meta", content=content, meta=meta)
    db.save_skrap(article, owner="process-meta")
    return article


def _get_html(db, name):
    return db.find_skrap_by_name("formatter", name)


def test_no_formatter_key_renders_as_markdown(skrapdb):
    _make_article(skrapdb, "foo.blog", "# Hello\n\nSome *text*.\n")

    FormatterPlugin(skrapdb, {}).run()

    html = _get_html(skrapdb, "foo.blog")
    assert html.content == "<h1>Hello</h1>\n<p>Some <em>text</em>.</p>\n"


def test_explicit_formatter_markdown_renders_as_markdown(skrapdb):
    _make_article(skrapdb, "foo.blog", "*hi*\n", formatter="markdown")

    FormatterPlugin(skrapdb, {}).run()

    assert _get_html(skrapdb, "foo.blog").content == "<p><em>hi</em></p>\n"


def test_formatter_raw_passes_content_through_unchanged(skrapdb):
    # Contains literal Markdown syntax that mistune would transform if
    # invoked by mistake (*text* -> <em>text</em>, plus <p> wrapping) -
    # a fixture that's inert under mistune wouldn't actually prove raw
    # content was never rendered. (A leading HTML-block tag like <div>
    # does NOT work for this: mistune treats it as a raw HTML block and
    # skips inline parsing inside it, so *text* would stay literal
    # either way - confirmed by testing it directly.)
    raw = "Some *text* that should stay literal, not become <em>.\n"
    _make_article(skrapdb, "foo.blog", raw, formatter="raw")

    FormatterPlugin(skrapdb, {}).run()

    assert _get_html(skrapdb, "foo.blog").content == raw


def test_unrecognized_formatter_fails_article(skrapdb):
    _make_article(skrapdb, "foo.blog", "body", formatter="reStructuredText")

    with pytest.raises(ArticleFailed):
        FormatterPlugin(skrapdb, {}).run()


def test_does_not_resave_when_nothing_changed(skrapdb):
    _make_article(skrapdb, "foo.blog", "hello\n")

    FormatterPlugin(skrapdb, {}).run()
    first = _get_html(skrapdb, "foo.blog").last_updated

    FormatterPlugin(skrapdb, {}).run()
    second = _get_html(skrapdb, "foo.blog").last_updated

    assert first == second


def test_rerenders_when_article_content_changes(skrapdb):
    _make_article(skrapdb, "foo.blog", "v1\n")
    FormatterPlugin(skrapdb, {}).run()

    article = skrapdb.find_skrap_by_name("process-meta", "foo.blog")
    article.content = "v2\n"
    skrapdb.save_skrap(article, owner="process-meta")
    FormatterPlugin(skrapdb, {}).run()

    assert _get_html(skrapdb, "foo.blog").content == "<p>v2</p>\n"
