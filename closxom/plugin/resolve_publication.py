"""Plugin to resolve publication state for articles.

See notes/redesign-decisions.md, "Publication model", for the design this
implements.
"""

from datetime import datetime

from closxom.plugin.base import Plugin
from closxom.pubdate import InvalidInstantValue, parse_published


class ResolvePublicationPlugin(Plugin):
    """Creates or updates one PublicationSkrap per ArticleSkrap, turning
    the raw `published:` META string (process_meta's `published_raw`)
    into `pubdate` (a UTC ISO-8601 instant, or absent) and `published`
    (0/1).

    published_raw  pubdate         published
    absent         absent          0
    a future date  that instant    0
    a past date    that instant    1

    published is recomputed every time an article's PublicationSkrap is
    rebuilt, from pubdate <= now; it is not an independently authored
    value. A malformed published_raw is treated the same as absent -
    the article is left unpublished with no pubdate - and logged.

    A PublicationSkrap's only dependency is its article, so under the
    standard staleness protocol it is only reconsidered when the
    article itself changes - not merely because wall-clock time has
    passed a future pubdate. See notes/redesign-decisions.md and
    `lt` vbstr7: making time itself a staleness input is deferred.
    """

    @classmethod
    def name(cls):
        return "resolve-publication"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["publication"]

    def default_target_list(self):
        return [a.name for a in self.db.find_all_skrap_by_type("article")]

    def dependencies_of(self, target):
        article = self.db.find_skrap_by_name("process-meta", target)
        return [article] if article else []

    def build_target(self, target):
        article = self.db.find_skrap_by_name("process-meta", target)
        if article is None:
            self.log.warning("No article skrap for target %r", target)
            return

        zone_name = self.config.get('timezone', 'America/New_York')
        raw = article.meta.get('published_raw')

        pubdate = None
        if raw:
            try:
                pubdate = parse_published(raw, zone_name)
            except InvalidInstantValue as e:
                self.log.error(
                    "%s: invalid published: value %r: %s", article.name, raw, e)

        published = pubdate is not None and datetime.fromisoformat(pubdate) <= self.now

        new_meta = {'published': int(published)}
        if pubdate is not None:
            new_meta['pubdate'] = pubdate

        publication = self.db.find_or_create_skrap("publication", target, self.name())
        self.reconcile_meta(publication, new_meta)
