"""Plugin to resolve publication state for articles.

See notes/redesign-decisions.md, "Publication model", for the design this
implements.
"""

from datetime import datetime

from closxom.plugin.base import Plugin
from closxom.pubdate import InvalidInstantValue, parse_published


class ResolvePublicationPlugin(Plugin):
    """Owns all publication logic: turns the raw `published:` META string
    (process_meta's `published_raw`) into `pubdate` (a UTC ISO-8601 instant,
    or absent) and `published` (0/1).

    published_raw  pubdate         published
    absent         absent          0
    a future date  that instant    0
    a past date    that instant    1

    published is recomputed every run from pubdate <= now; it is not an
    independently authored value. A malformed published_raw is treated the
    same as absent - the article is left unpublished with no pubdate - and
    logged; must run after process_meta.
    """

    @classmethod
    def name(cls):
        return "resolve-publication"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return []  # Modifies articles in place

    def run(self):
        """Resolve pubdate/published for all articles."""
        articles = self.db.find_all_skrap_by_type("article")
        zone_name = self.config.get('timezone', 'America/New_York')

        resolved = 0
        for article in articles:
            raw = article.meta.get('published_raw')

            pubdate = None
            if raw:
                try:
                    pubdate = parse_published(raw, zone_name)
                except InvalidInstantValue as e:
                    self.log.error(
                        "%s: invalid published: value %r: %s", article.name, raw, e)

            published = pubdate is not None and datetime.fromisoformat(pubdate) <= self.now

            changed = False
            if pubdate != article.meta.get('pubdate'):
                if pubdate is None:
                    del article.meta['pubdate']
                else:
                    article.meta['pubdate'] = pubdate
                changed = True

            if int(published) != article.meta.get('published'):
                article.meta['published'] = int(published)
                changed = True

            if changed:
                self.db.save_skrap(article)
                resolved += 1

        return resolved
