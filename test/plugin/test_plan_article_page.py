from closxom.plugin.plan_article_page import PlanArticlePagePlugin
from closxom.skrap import ArticleSkrap, HTMLSkrap, PublicationSkrap


def _make_published(db, name, title="Title", pubdate="2027-01-01T00:00:00+00:00",
                     html_content="<p>body</p>\n"):
    article = ArticleSkrap(name=name, owner="process-meta", meta={'title': title})
    db.save_skrap(article, owner="process-meta")

    publication = PublicationSkrap(name=name, owner="resolve-publication",
                                    meta={'pubdate': pubdate, 'published': 1})
    db.save_skrap(publication, owner="resolve-publication")

    html = HTMLSkrap(name=name, owner="formatter", content=html_content)
    db.save_skrap(html, owner="formatter")


def _get_plan(db, output_name):
    return db.find_skrap_by_name("plan-article-page", output_name)


def test_creates_plan_for_published_article(skrapdb):
    _make_published(skrapdb, "foo.blog", title="Foo", pubdate="2027-01-01T00:00:00+00:00")

    PlanArticlePagePlugin(skrapdb, {}).run()

    plan = _get_plan(skrapdb, "foo.html")
    assert plan is not None
    assert plan.meta['template'] == 'single_article'
    assert plan.meta['values'] == {'title': 'Foo', 'pubdate': '2027-01-01T00:00:00+00:00'}
    assert plan.meta['built_from'] == [{'owner': 'formatter', 'name': 'foo.blog'}]
    assert plan.meta['output_path'] == 'foo.html'


def test_output_name_preserves_subdirectory(skrapdb):
    _make_published(skrapdb, "dir/bar.blog", title="Bar")

    PlanArticlePagePlugin(skrapdb, {}).run()

    assert _get_plan(skrapdb, "dir/bar.html") is not None


def test_unpublished_article_has_no_plan(skrapdb):
    article = ArticleSkrap(name="foo.blog", owner="process-meta", meta={'title': 'Foo'})
    skrapdb.save_skrap(article, owner="process-meta")
    publication = PublicationSkrap(name="foo.blog", owner="resolve-publication",
                                    meta={'published': 0})
    skrapdb.save_skrap(publication, owner="resolve-publication")
    # No HTMLSkrap either - formatter only ever renders articles process_meta
    # has already created; irrelevant here since the article is unpublished.

    PlanArticlePagePlugin(skrapdb, {}).run()

    assert _get_plan(skrapdb, "foo.html") is None


def test_does_not_resave_when_nothing_changed(skrapdb):
    _make_published(skrapdb, "foo.blog")
    PlanArticlePagePlugin(skrapdb, {}).run()
    first = _get_plan(skrapdb, "foo.html").last_updated

    PlanArticlePagePlugin(skrapdb, {}).run()
    second = _get_plan(skrapdb, "foo.html").last_updated

    assert first == second


def test_unrelated_html_touch_does_not_resave_plan(skrapdb):
    # The plan only references the html skrap by name, not by content, so
    # a dependency that looks stale to run()'s coarse last_updated check
    # must not cause a needless resave when nothing the plan actually
    # records has changed.
    _make_published(skrapdb, "foo.blog", html_content="<p>same</p>\n")
    PlanArticlePagePlugin(skrapdb, {}).run()
    first = _get_plan(skrapdb, "foo.html").last_updated

    html = skrapdb.find_skrap_by_name("formatter", "foo.blog")
    html.content = "<p>same</p>\n"
    skrapdb.save_skrap(html, owner="formatter")

    PlanArticlePagePlugin(skrapdb, {}).run()

    assert _get_plan(skrapdb, "foo.html").last_updated == first


def test_replans_when_title_changes(skrapdb):
    _make_published(skrapdb, "foo.blog", title="Old Title")
    PlanArticlePagePlugin(skrapdb, {}).run()

    article = skrapdb.find_skrap_by_name("process-meta", "foo.blog")
    article.meta['title'] = "New Title"
    skrapdb.save_skrap(article, owner="process-meta")

    PlanArticlePagePlugin(skrapdb, {}).run()

    assert _get_plan(skrapdb, "foo.html").meta['values']['title'] == "New Title"
