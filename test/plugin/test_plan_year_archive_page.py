from closxom.plugin.plan_year_archive_page import PlanYearArchivePagePlugin
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
    return db.find_skrap_by_name("plan-year-archive-page", output_name)


def test_creates_plan_for_year_with_published_articles(skrapdb):
    _make_published(skrapdb, "foo.blog", title="Foo", pubdate="2027-03-01T00:00:00+00:00")

    PlanYearArchivePagePlugin(skrapdb, {}).run()

    plan = _get_plan(skrapdb, "2027/index.html")
    assert plan is not None
    assert plan.meta['template'] == 'archive'
    assert plan.meta['values']['title'] == "Articles from 2027"
    assert plan.meta['values']['articles'] == [{
        'title': 'Foo',
        'date': '2027-03-01T00:00:00+00:00',
        'content': '<p>body</p>\n',
        'url': 'foo.html',
    }]
    assert plan.meta['built_from'] == [{'owner': 'formatter', 'name': 'foo.blog'}]
    assert plan.meta['output_path'] == '2027/index.html'


def test_multiple_articles_same_year_sorted_newest_first(skrapdb):
    _make_published(skrapdb, "jan.blog", title="January", pubdate="2027-01-01T00:00:00+00:00")
    _make_published(skrapdb, "jun.blog", title="June", pubdate="2027-06-01T00:00:00+00:00")

    PlanYearArchivePagePlugin(skrapdb, {}).run()

    titles = [a['title'] for a in _get_plan(skrapdb, "2027/index.html").meta['values']['articles']]
    assert titles == ["June", "January"]


def test_different_years_get_different_plans(skrapdb):
    _make_published(skrapdb, "old.blog", title="Old", pubdate="2020-01-01T00:00:00+00:00")
    _make_published(skrapdb, "new.blog", title="New", pubdate="2027-01-01T00:00:00+00:00")

    PlanYearArchivePagePlugin(skrapdb, {}).run()

    assert [a['title'] for a in _get_plan(skrapdb, "2020/index.html").meta['values']['articles']] == ["Old"]
    assert [a['title'] for a in _get_plan(skrapdb, "2027/index.html").meta['values']['articles']] == ["New"]


def test_unpublished_article_excluded(skrapdb):
    article = ArticleSkrap(name="foo.blog", owner="process-meta", meta={'title': 'Foo'})
    skrapdb.save_skrap(article, owner="process-meta")
    publication = PublicationSkrap(name="foo.blog", owner="resolve-publication",
                                    meta={'published': 0})
    skrapdb.save_skrap(publication, owner="resolve-publication")

    PlanYearArchivePagePlugin(skrapdb, {}).run()

    assert skrapdb.find_all_skrap_by_type("plan") == []


def test_does_not_resave_when_nothing_changed(skrapdb):
    _make_published(skrapdb, "foo.blog")
    PlanYearArchivePagePlugin(skrapdb, {}).run()
    first = _get_plan(skrapdb, "2027/index.html").last_updated

    PlanYearArchivePagePlugin(skrapdb, {}).run()
    second = _get_plan(skrapdb, "2027/index.html").last_updated

    assert first == second


def test_adding_an_article_updates_the_existing_year_plan(skrapdb):
    _make_published(skrapdb, "jan.blog", title="January", pubdate="2027-01-01T00:00:00+00:00")
    PlanYearArchivePagePlugin(skrapdb, {}).run()
    assert len(_get_plan(skrapdb, "2027/index.html").meta['values']['articles']) == 1

    _make_published(skrapdb, "jun.blog", title="June", pubdate="2027-06-01T00:00:00+00:00")
    PlanYearArchivePagePlugin(skrapdb, {}).run()

    titles = [a['title'] for a in _get_plan(skrapdb, "2027/index.html").meta['values']['articles']]
    assert sorted(titles) == ["January", "June"]


def test_year_with_no_remaining_articles_leaves_existing_plan_untouched(skrapdb):
    _make_published(skrapdb, "foo.blog", pubdate="2027-01-01T00:00:00+00:00")
    PlanYearArchivePagePlugin(skrapdb, {}).run()
    before = _get_plan(skrapdb, "2027/index.html").meta
    before_updated = _get_plan(skrapdb, "2027/index.html").last_updated

    publication = skrapdb.find_skrap_by_name("resolve-publication", "foo.blog")
    publication.meta['published'] = 0
    skrapdb.save_skrap(publication, owner="resolve-publication")

    PlanYearArchivePagePlugin(skrapdb, {}).run()

    # Whether build_target actually ran-and-no-opped, or never ran at all
    # because dependencies_of() now returns nothing left to look stale
    # against (see lt yhhrg5), isn't something to assert on - only that
    # the plan is left alone either way.
    assert _get_plan(skrapdb, "2027/index.html").meta == before
    assert _get_plan(skrapdb, "2027/index.html").last_updated == before_updated
