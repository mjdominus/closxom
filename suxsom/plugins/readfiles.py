"""Plugin to read file contents and create ArticleSux products."""

from pathlib import Path
from suxsom.plugin.plugin import Plugin
from suxsom.sux import ArticleSux


class ReadFilesPlugin(Plugin):
    """Reads file contents and creates ArticleSux products.

    Consumes FileSux products and produces ArticleSux products with
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
        file_suxes = self.db.find_all_sux_by_type("file")

        articles_created = 0
        for file_sux in file_suxes:
            path = Path(file_sux.meta['path'])

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

            # Create article sux with raw content
            article = ArticleSux(
                name=file_sux.name,
                owner=self.name(),
                meta={
                    'original_content': content,
                    'path': file_sux.meta['path'],
                    'relpath': file_sux.meta['relpath'],
                    'mtime': file_sux.meta['mtime']
                }
            )

            self.db.save_sux(article)
            articles_created += 1

        return articles_created
