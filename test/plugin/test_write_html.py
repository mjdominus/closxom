import os

import pytest

from closxom.plugin.write_html import WriteHtmlPlugin
from closxom.skrap import PlanSkrap


def _make_plan(db, name, title="Title", pubdate="2027-01-01T00:00:00+00:00",
                html_content="<p>body</p>\n", output_path=None):
    html = db.find_or_create_skrap("html", name, "formatter")
    html.content = html_content
    db.save_skrap(html, owner="formatter")

    plan = db.find_or_create_skrap("plan", name, "plan-article-page")
    plan.meta.update({
        'template': 'single_article',
        # Deliberately mismatched from the article's own title below -
        # render_single_article must never read this for 'single_article'
        # (see plan_article_page.py), so a correct render always shows
        # `title`, never this sentinel.
        'values': {'title': '(dummy page title, should never render)', 'articles': [{
            'title': title,
            'date': pubdate,
            'content': html_content,
            'url': output_path or name,
        }]},
        'built_from': [{'owner': 'formatter', 'name': name}],
        'output_path': output_path or name,
    })
    db.save_skrap(plan, owner="plan-article-page")
    return plan


def test_writes_html_file(skrapdb, tmp_path):
    _make_plan(skrapdb, "foo.html", title="Foo", html_content="<p>hello</p>\n")

    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    written = (tmp_path / "foo.html").read_text()
    assert "<title>Foo</title>" in written
    assert "<h1>Foo</h1>" in written
    assert "<p>hello</p>" in written
    assert "January 01, 2027" in written


def test_explicit_target_list_limits_which_plans_are_written(skrapdb, tmp_path):
    _make_plan(skrapdb, "a.html", title="A")
    _make_plan(skrapdb, "b.html", title="B")

    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run(["a.html"])

    assert (tmp_path / "a.html").exists()
    assert not (tmp_path / "b.html").exists()


def test_creates_nested_output_directories(skrapdb, tmp_path):
    _make_plan(skrapdb, "dir/bar.html", output_path="dir/bar.html")

    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    assert (tmp_path / "dir" / "bar.html").exists()


def test_title_is_escaped_but_body_content_is_not(skrapdb, tmp_path):
    _make_plan(skrapdb, "foo.html", title="A <b>Title</b>",
               html_content="<p>already <em>HTML</em></p>\n")

    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    written = (tmp_path / "foo.html").read_text()
    assert "<title>A &lt;b&gt;Title&lt;/b&gt;</title>" in written
    assert "<p>already <em>HTML</em></p>" in written


def test_does_not_rewrite_up_to_date_output(skrapdb, tmp_path):
    _make_plan(skrapdb, "foo.html")
    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    output_file = tmp_path / "foo.html"
    original_mtime = output_file.stat().st_mtime
    original_content = output_file.read_text()

    # Overwrite by hand so a resave would be detectable, then rerun -
    # since the output file is already at least as new as the plan, it
    # must be left alone.
    output_file.write_text("UNTOUCHED")
    os.utime(output_file, (original_mtime + 1000, original_mtime + 1000))

    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    assert output_file.read_text() == "UNTOUCHED"


def test_rewrites_when_plan_is_newer_than_existing_output(skrapdb, tmp_path):
    _make_plan(skrapdb, "foo.html", title="Old")
    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    output_file = tmp_path / "foo.html"
    os.utime(output_file, (0, 0))  # make the existing file look ancient

    _make_plan(skrapdb, "foo.html", title="New")
    WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    assert "New" in output_file.read_text()


def test_single_article_template_warns_on_multiple_articles(skrapdb, tmp_path, caplog):
    plan = skrapdb.find_or_create_skrap("plan", "foo.html", "plan-article-page")
    plan.meta.update({
        'template': 'single_article',
        'values': {'articles': [
            {'title': 'First', 'date': None, 'content': '<p>1</p>', 'url': 'foo.html'},
            {'title': 'Second', 'date': None, 'content': '<p>2</p>', 'url': 'foo.html'},
        ]},
        'built_from': [],
        'output_path': 'foo.html',
    })
    skrapdb.save_skrap(plan, owner="plan-article-page")

    with caplog.at_level("WARNING"):
        WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()

    assert any("expects one article" in r.message for r in caplog.records)
    # Uses only the first article, not both.
    written = (tmp_path / "foo.html").read_text()
    assert "First" in written
    assert "Second" not in written


def test_unknown_template_raises(skrapdb, tmp_path):
    plan = PlanSkrap(name="foo.html", owner="plan-article-page", meta={
        'template': 'mystery',
        'values': {},
        'built_from': [],
        'output_path': 'foo.html',
    })
    skrapdb.save_skrap(plan, owner="plan-article-page")

    with pytest.raises(ValueError):
        WriteHtmlPlugin(skrapdb, {'output_dir': str(tmp_path)}).run()
