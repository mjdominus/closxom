"""Plugin to build date archive pages."""

from datetime import datetime
from collections import defaultdict
from suxsom.plugin.plugin import Plugin
from suxsom.sux import PageSux


class BuildDateArchivesPlugin(Plugin):
    """Creates PageSux products for date-based archives.

    Groups articles by year and month, creating archive pages for each.
    """

    @classmethod
    def name(cls):
        return "build-date-archives"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["page"]

    def run(self):
        """Create date archive pages."""
        articles = self.db.find_all_sux_by_type("article")

        # Group articles by year and month
        year_archives = defaultdict(list)
        month_archives = defaultdict(list)

        for article in articles:
            # Only include published articles
            if not article.meta.get('published', True):
                continue

            date = article.meta.get('date')
            if date is None:
                continue

            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(date)
            year = dt.year
            month = (dt.year, dt.month)

            year_archives[year].append(article.id)
            month_archives[month].append(article.id)

        pages_created = 0

        # Create year archive pages
        for year, article_ids in year_archives.items():
            # Sort by date (newest first)
            article_ids_sorted = self.sort_articles_by_date(article_ids, reverse=True)

            page = PageSux(
                name=f"archive:year:{year}",
                owner=self.name(),
                meta={
                    'article_ids': article_ids_sorted,
                    'output_path': f"{year}/index.html",
                    'page_type': 'date_archive_year',
                    'title': f"Articles from {year}",
                    'year': year
                }
            )

            self.db.save_sux(page)
            pages_created += 1

        # Create month archive pages
        for (year, month), article_ids in month_archives.items():
            # Sort by date (newest first)
            article_ids_sorted = self.sort_articles_by_date(article_ids, reverse=True)

            month_name = datetime(year, month, 1).strftime('%B')

            page = PageSux(
                name=f"archive:month:{year}-{month:02d}",
                owner=self.name(),
                meta={
                    'article_ids': article_ids_sorted,
                    'output_path': f"{year}/{month:02d}/index.html",
                    'page_type': 'date_archive_month',
                    'title': f"Articles from {month_name} {year}",
                    'year': year,
                    'month': month
                }
            )

            self.db.save_sux(page)
            pages_created += 1

        return pages_created

    def sort_articles_by_date(self, article_ids, reverse=False):
        """Sort article IDs by their publication date."""
        articles_with_dates = []

        for article_id in article_ids:
            article = self.db.find_sux_by_id(article_id)
            if article and 'date' in article.meta:
                articles_with_dates.append((article.meta['date'], article_id))

        articles_with_dates.sort(reverse=reverse)
        return [aid for (_, aid) in articles_with_dates]
