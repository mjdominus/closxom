import os

import pytest

from closxom.plugins.scanfiles import ScanFilesPlugin


@pytest.fixture
def articles_dir(tmp_path):
    # A subdirectory of tmp_path, distinct from wherever the skrapdb
    # fixture puts its sqlite file, so scanfiles doesn't pick up the
    # database itself while walking the input directory.
    d = tmp_path / "articles"
    d.mkdir()
    return d


def test_scanfiles_captures_file_content(skrapdb, articles_dir):
    (articles_dir / "foo.blog").write_text("the body text")

    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()

    files = skrapdb.find_all_skrap_by_type("file")
    assert len(files) == 1
    assert files[0].content == "the body text"


def test_scanfiles_rerun_updates_changed_file(skrapdb, articles_dir):
    article_path = articles_dir / "foo.blog"
    article_path.write_text("original content")

    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()

    files = skrapdb.find_all_skrap_by_type("file")
    assert len(files) == 1
    original_mtime = files[0].meta['file_mtime']

    # Bump the mtime forward so the change is unambiguous regardless of
    # filesystem mtime resolution.
    new_mtime = original_mtime + 10
    article_path.write_text("updated content")
    os.utime(article_path, (new_mtime, new_mtime))

    # Rerunning must not crash (the UNIQUE(name, owner_id) constraint bug)
    # and must notice the changed mtime.
    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()

    files = skrapdb.find_all_skrap_by_type("file")
    assert len(files) == 1
    assert files[0].meta['file_mtime'] == new_mtime
    assert files[0].content == "updated content"


def test_scanfiles_skips_unchanged_file(skrapdb, articles_dir):
    (articles_dir / "foo.blog").write_text("original content")

    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()
    first_last_updated = skrapdb.find_all_skrap_by_type("file")[0].last_updated

    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()
    second_last_updated = skrapdb.find_all_skrap_by_type("file")[0].last_updated

    assert first_last_updated == second_last_updated


def test_scanfiles_detects_notyet_marker(skrapdb, articles_dir):
    (articles_dir / "foo.blog").write_text("original content")
    (articles_dir / "foo.blog.notyet").touch()

    ScanFilesPlugin(skrapdb, {'input_dir': str(articles_dir)}).run()

    files = skrapdb.find_all_skrap_by_type("file")
    assert len(files) == 1
    # Booleans don't round-trip through the meta store (no bool type in
    # SQLite, and _load_metadata's json.loads only fires on str/bytes) -
    # True comes back as 1. See TODO.md's metadata-typing item.
    assert files[0].meta['has_notyet']
