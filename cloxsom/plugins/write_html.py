"""Plugin to write HTML output files."""

from pathlib import Path
from datetime import datetime
from cloxsom.plugin.plugin import Plugin


class WriteHtmlPlugin(Plugin):
    """Writes HTML files from PageSkrap products.

    Consumes PageSkrap products and writes HTML files to the output directory.
    """

    @classmethod
    def name(cls):
        return "write-html"

    @classmethod
    def inputs(cls):
        return ["page"]

    @classmethod
    def outputs(cls):
        return []  # Writes to filesystem

    def __init__(self, db, output_dir=None):
        """Initialize the HTML writer.

        Args:
            db: Database handle
            output_dir: Directory to write output (defaults to 'output')
        """
        super().__init__(db)
        self.output_dir = Path(output_dir) if output_dir else Path("output")

    def run(self):
        """Write HTML files for all pages."""
        pages = self.db.find_all_skrap_by_type("page")

        files_written = 0
        for page in pages:
            output_path = self.output_dir / page.meta['output_path']

            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate HTML content
            html = self.generate_html(page)

            # Write file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            files_written += 1

        return files_written

    def generate_html(self, page):
        """Generate HTML content for a page."""
        page_type = page.meta.get('page_type', 'unknown')
        title = page.meta.get('title', 'Untitled')

        # Get articles for this page
        article_ids = page.meta.get('article_ids', [])
        articles = [self.db.find_skrap_by_id(aid) for aid in article_ids]
        articles = [a for a in articles if a is not None]

        # Generate page based on type
        if page_type == 'single':
            return self.generate_single_article_page(page, articles[0] if articles else None)
        elif page_type in ['date_archive_year', 'date_archive_month', 'topic_archive', 'main']:
            return self.generate_archive_page(page, articles)
        else:
            return self.generate_generic_page(page, articles)

    def generate_single_article_page(self, page, article):
        """Generate HTML for a single article page."""
        if article is None:
            return "<html><body>Article not found</body></html>"

        title = article.meta.get('title', 'Untitled')
        content = article.meta.get('content', '')
        date = article.meta.get('date')

        date_str = ''
        if date:
            dt = datetime.fromtimestamp(date)
            date_str = f"<p class='date'>{dt.strftime('%B %d, %Y')}</p>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.escape_html(title)}</title>
</head>
<body>
    <article>
        <h1>{self.escape_html(title)}</h1>
        {date_str}
        <div class='content'>
{self.escape_html(content)}
        </div>
    </article>
</body>
</html>"""

    def generate_archive_page(self, page, articles):
        """Generate HTML for an archive page."""
        title = page.meta.get('title', 'Archive')

        article_list = []
        for article in articles:
            art_title = article.meta.get('title', 'Untitled')
            art_date = article.meta.get('date')
            art_relpath = article.meta.get('relpath', '')

            # Convert article path to URL
            url = art_relpath.rsplit('.', 1)[0] + '.html' if art_relpath else '#'

            date_str = ''
            if art_date:
                dt = datetime.fromtimestamp(art_date)
                date_str = f" <span class='date'>({dt.strftime('%Y-%m-%d')})</span>"

            article_list.append(f"<li><a href='/{url}'>{self.escape_html(art_title)}</a>{date_str}</li>")

        articles_html = '\n'.join(article_list)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.escape_html(title)}</title>
</head>
<body>
    <h1>{self.escape_html(title)}</h1>
    <ul class='article-list'>
{articles_html}
    </ul>
</body>
</html>"""

    def generate_generic_page(self, page, articles):
        """Generate HTML for a generic page."""
        title = page.meta.get('title', 'Page')
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.escape_html(title)}</title>
</head>
<body>
    <h1>{self.escape_html(title)}</h1>
    <p>Generic page with {len(articles)} articles</p>
</body>
</html>"""

    def escape_html(self, text):
        """Escape HTML special characters."""
        if text is None:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
