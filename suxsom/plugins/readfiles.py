"""Plugin to read file contents and create ArticleSkrap products."""

from pathlib import Path
from suxsom.plugin.plugin import Plugin
from suxsom.skrap import ArticleSkrap


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
        file_skrapes = self.db.find_all_skrap_by_type("file")

        articles_created = 0
        for file_skrap in file_skrapes:
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

            # Create article skrap with raw content
            article = ArticleSkrap(
                name=file_skrap.name,
                owner=self.name(),
                meta={
                    'original_content': content,
                    'path': file_skrap.meta['path'],
                    'relpath': file_skrap.meta['relpath'],
                    'mtime': file_skrap.meta['mtime']
                }
            )

            self.db.save_skrap(article)
            articles_created += 1

        return articles_created
