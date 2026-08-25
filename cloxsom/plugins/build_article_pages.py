"""Plugin to build single-article pages."""

from cloxsom.plugin.plugin import Plugin
from cloxsom.skrap import PageSkrap


class BuildArticlePagesPlugin(Plugin):
    """Creates PageSkrap products for individual articles.

    Consumes ArticleSkrap products and produces PageSkrap products for
    single-article pages.
    """

    @classmethod
    def name(cls):
        return "build-article-pages"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["page"]

    def run(self):
        """Create a page for each published article."""
        articles = self.db.find_all_skrap_by_type("article")

        pages_created = 0
        for article in articles:
            # Only create pages for published articles
            if not article.meta.get('published', True):
                continue

            # Determine output path from article relpath
            # e.g., "tech/foo.txt" -> "tech/foo.html"
            relpath = article.meta.get('relpath', '')
            if relpath:
                # Replace extension with .html
                output_path = relpath.rsplit('.', 1)[0] + '.html'
            else:
                output_path = f"article_{article.id}.html"

            # Create page skrap
            page = PageSkrap(
                name=f"page:{relpath}",
                owner=self.name(),
                meta={
                    'article_ids': [article.id],
                    'output_path': output_path,
                    'page_type': 'single',
                    'title': article.meta.get('title', 'Untitled')
                }
            )

            self.db.save_skrap(page)
            pages_created += 1

        return pages_created
