"""Plugin to compute publication dates for articles."""

from datetime import datetime
from closxom.plugin.plugin import Plugin


class ComputeDatesPlugin(Plugin):
    """Computes publication dates for articles.

    Uses metadata 'date' field if present, otherwise falls back to
    file modification time.
    """

    @classmethod
    def name(cls):
        return "compute-dates"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return []  # Modifies articles in place

    def run(self):
        """Compute publication dates for all articles."""
        articles = self.db.find_all_skrap_by_type("article")

        computed = 0
        for article in articles:
            # Skip if already has a parsed date
            if 'date' in article.meta and isinstance(article.meta['date'], (int, float)):
                continue

            date_timestamp = None

            # Try to parse from META date field
            if 'date' in article.meta and isinstance(article.meta['date'], str):
                date_timestamp = self.parse_date_string(article.meta['date'])

            # Fall back to file mtime
            if date_timestamp is None:
                date_timestamp = article.meta.get('file_mtime')

            if date_timestamp is not None:
                article.meta['date'] = date_timestamp
                self.db.save_skrap(article)
                computed += 1

        return computed

    def parse_date_string(self, date_str):
        """Parse a date string to Unix timestamp.

        Supports formats like:
        - YYYY-MM-DD
        - YYYY/MM/DD
        - Unix timestamp
        """
        # Try parsing as Unix timestamp
        try:
            return float(date_str)
        except ValueError:
            pass

        # Try parsing as ISO date
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue

        return None
