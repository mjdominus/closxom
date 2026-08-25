"""Plugin to filter out unpublished articles."""

from pathlib import Path
from suxsom.plugin.plugin import Plugin


class NotYetPlugin(Plugin):
    """Marks articles as unpublished if they have a .notyet file.

    Modifies existing ArticleSkrap products in place, setting their
    'published' metadata to False if a corresponding .notyet file exists.
    """

    @classmethod
    def name(cls):
        return "notyet"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return []  # Modifies articles in place, doesn't create new products

    def run(self):
        """Check for .notyet files and mark articles as unpublished."""
        articles = self.db.find_all_skrap_by_type("article")

        marked_unpublished = 0
        for article in articles:
            # Check if .notyet file exists
            path = Path(article.meta['path'])
            notyet_path = path.parent / (path.name + '.notyet')

            if notyet_path.exists():
                article.meta['published'] = False
                self.db.save_skrap(article)
                marked_unpublished += 1
            elif 'published' not in article.meta:
                # Default to published if not specified
                article.meta['published'] = True
                self.db.save_skrap(article)

        return marked_unpublished
