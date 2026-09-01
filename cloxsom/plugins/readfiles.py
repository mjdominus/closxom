"""Plugin to read file contents and create ArticleSkrap products."""

from pathlib import Path
from cloxsom.plugin.plugin import Plugin
from cloxsom.skrap import ArticleSkrap


class ReadFilesPlugin(Plugin):
    """Reads file contents and creates ArticleSkrap products.

    Consumes FileSkrap products and produces ArticleSkrap products with
    the raw file content loaded.
    """

    @classmethod
    def name(cls):
        return "readfiles"

    @classmethod
    def inputs(cls):
        return ["file"]

    @classmethod
    def outputs(cls):
        return ["article"]

    def default_target_list(self):
        return [f.name for f in self.db.find_all_skrap_by_type("file")]

    def dependencies_of(self, target):
        file_skrap = self.db.find_skrap_by_name("scanfiles", target)
        return [file_skrap] if file_skrap else []

    def build_target(self, target):
        file_skrap = self.db.find_skrap_by_name("scanfiles", target)
        path = Path(file_skrap.meta['path'])

        if not path.exists():
            self.log.warning("File not found: %s", path)
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                new_content = f.read()
        except OSError as e:
            self.log.warning("Could not read %s: %s", path, e)
            return

        # A newer FileSkrap.last_updated (what triggered this build_target
        # call) doesn't mean the file's content actually changed - e.g. a
        # benign mtime touch, or scanfiles resaving unconditionally. Only
        # touch the article (and so only bump its last_updated) if the
        # content actually differs, otherwise leave it and everything
        # downstream (process_meta, etc.) already did to it alone.
        if file_skrap.content == new_content:
            self.log.info("Skipping target %r: content unchanged", target)
            return

        file_skrap.content = new_content
        self.db.save_skrap(file_skrap)

        new_meta = {
            'path': file_skrap.meta['path'],
            'relpath': file_skrap.meta['relpath'],
            'file_mtime': file_skrap.meta['file_mtime']
        }

        # Update the existing article skrap in place if one already
        # exists for this name, rather than trying to insert a second
        # row and hitting the UNIQUE(name, owner_id) constraint.
        article = self.db.find_skrap_by_name(self.name(), target)
        if article is None:
            article = ArticleSkrap(name=target, owner=self.name(), meta=new_meta)
        else:
            article.meta.update(new_meta)

        article.content = new_content
        self.db.save_skrap(article)
