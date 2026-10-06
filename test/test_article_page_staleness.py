"""Integration test for the plan_article_page -> write_html pipeline's
staleness handling - specifically the bug where a body-only edit (title
and pubdate unchanged) never reaches the written output file."""

from closxom.plugin.formatter import FormatterPlugin
from closxom.plugin.plan_article_page import PlanArticlePagePlugin
from closxom.plugin.write_html import WriteHtmlPlugin
from closxom.skrap import ArticleSkrap, PublicationSkrap


def _make_article(db, name, title, content):
    article = ArticleSkrap(name=name, owner="process-meta", content=content,
                            meta={'title': title})
    db.save_skrap(article, owner="process-meta")

    publication = db.find_or_create_skrap("publication", name, "resolve-publication")
    publication.meta.update({'pubdate': '2027-01-01T00:00:00+00:00', 'published': 1})
    db.save_skrap(publication, owner="resolve-publication")


def _plan_and_write(db, output_dir):
    FormatterPlugin(db, {}).run()
    PlanArticlePagePlugin(db, {}).run()
    WriteHtmlPlugin(db, {'output_dir': str(output_dir)}).run()


def test_body_only_edit_reaches_the_written_file(skrapdb, tmp_path):
    _make_article(skrapdb, "foo.blog", "Foo", "Version one.\n")
    _plan_and_write(skrapdb, tmp_path)
    assert "Version one." in (tmp_path / "foo.html").read_text()

    article = skrapdb.find_skrap_by_name("process-meta", "foo.blog")
    article.content = "Version TWO, totally different text.\n"
    skrapdb.save_skrap(article, owner="process-meta")
    _plan_and_write(skrapdb, tmp_path)

    written = (tmp_path / "foo.html").read_text()
    assert "Version TWO, totally different text." in written
    assert "Version one." not in written
