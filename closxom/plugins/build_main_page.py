"""Plugin to build the main index page."""

from closxom.plugin.plugin import Plugin
from closxom.skrap import PageSkrap


class BuildMainPagePlugin(Plugin):
    """Creates a main index page with recent articles.

    Shows the N most recent published articles.
    """

    @classmethod
    def name(cls):
        return "build-main-page"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["page"]

    def __init__(self, db, config=None):
        """Initialize the main page builder.

        Reads config['recent'] (defaults to 12).
        """
        super().__init__(db, config)
        self.num_recent = self.config.get('recent', 12)

    def run(self):
        """Create the main index page."""
        articles = self.db.find_all_published_articles()

        # Get published articles with dates
        published_articles = []
        for article in articles:
            if 'date' in article.meta:
                published_articles.append((article.meta['date'], article.id))

        # Sort by date (newest first) and take top N
        published_articles.sort(reverse=True)
        recent_article_ids = [aid for (_, aid) in published_articles[:self.num_recent]]

        # Create main page
        page = PageSkrap(
            name="main:index",
            owner=self.name(),
            meta={
                'article_ids': recent_article_ids,
                'output_path': 'index.html',
                'page_type': 'main',
                'title': 'Recent Articles'
            }
        )

        self.db.save_skrap(page)
        return 1
