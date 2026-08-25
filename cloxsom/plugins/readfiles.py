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

    def run(self):
        """Read all files and create article products."""
        file_skraps = self.db.find_all_skrap_by_type("file")

        articles_created = 0
        for file_skrap in file_skraps:
            path = Path(file_skrap.meta['path'])

            if not path.exists():
                print(f"Warning: File not found: {path}")
                continue

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}")
                continue

            new_meta = {
                'original_content': content,
                'path': file_skrap.meta['path'],
                'relpath': file_skrap.meta['relpath'],
                'file_mtime': file_skrap.meta['file_mtime']
            }

            # Update the existing article skrap in place if one already
            # exists for this name, rather than trying to insert a second
            # row and hitting the UNIQUE(name, owner_id) constraint.
            article = self.db.find_skrap_by_name(self.name(), file_skrap.name)
            if article is None:
                article = ArticleSkrap(name=file_skrap.name, owner=self.name(), meta=new_meta)
            else:
                article.meta.update(new_meta)

            self.db.save_skrap(article)
            articles_created += 1

        return articles_created
