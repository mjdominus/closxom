from cloxsom.plugins.readfiles import ReadFilesPlugin
from cloxsom.skrap import FileSkrap


def _scan_one_file(db, path):
    file_skrap = FileSkrap(
        name=path.name,
        owner="scanfiles",
        meta={
            'path': str(path),
            'relpath': path.name,
            'file_mtime': path.stat().st_mtime,
        },
    )
    db.save_skrap(file_skrap)


def test_readfiles_rerun_updates_existing_article(skrapdb, tmp_path):
    article_path = tmp_path / "foo.blog"
    article_path.write_text("original content")
    _scan_one_file(skrapdb, article_path)

    ReadFilesPlugin(skrapdb, {}).run()

    article_path.write_text("updated content")
    # Simulate scanfiles noticing the file changed and re-saving the
    # FileSkrap, which is what readfiles' staleness check now depends on.
    file_skrap = skrapdb.find_skrap_by_name("scanfiles", article_path.name)
    file_skrap.meta['file_mtime'] = article_path.stat().st_mtime
    skrapdb.save_skrap(file_skrap)

    ReadFilesPlugin(skrapdb, {}).run()

    articles = skrapdb.find_all_skrap_by_type("article")
    assert len(articles) == 1
    assert articles[0].content == "updated content"
