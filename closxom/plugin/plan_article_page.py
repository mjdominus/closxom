"""Plugin to plan a single-article output page for each published article."""

from closxom.plugin.base import Plugin


class PlanArticlePagePlugin(Plugin):
    """Creates or updates one PlanSkrap per published article's output
    page, naming it after the output file it pertains to (e.g.
    `dir/bar.blog` -> `dir/bar.html`) rather than the input article -
    see notes/redesign-decisions.md and PlanSkrap's docstring.
    """

    @classmethod
    def name(cls):
        return "plan-article-page"

    @classmethod
    def inputs(cls):
        return ["article", "publication", "html"]

    @classmethod
    def outputs(cls):
        return ["plan"]

    def default_target_list(self):
        return [self._output_name(a) for a in self.db.find_all_published_articles()]

    def dependencies_of(self, target):
        article = self._article_for_output(target)
        if article is None:
            return []
        deps = [article]
        publication = self.db.find_skrap_by_name("resolve-publication", article.name)
        if publication is not None:
            deps.append(publication)
        html = self.db.find_skrap_by_name("formatter", article.name)
        if html is not None:
            deps.append(html)
        return deps

    def build_target(self, target):
        article = self._article_for_output(target)
        if article is None:
            self.log.warning("No published article maps to output %r", target)
            return

        publication = self.db.find_skrap_by_name("resolve-publication", article.name)
        html = self.db.find_skrap_by_name("formatter", article.name)
        if html is None:
            self.log.warning("No rendered HTML for %r yet", article.name)
            return

        new_meta = {
            'template': 'single_article',
            'values': {
                'title': article.meta.get('title', 'Untitled'),
                'pubdate': publication.meta.get('pubdate') if publication else None,
            },
            'built_from': [{'owner': 'formatter', 'name': article.name}],
            'output_path': target,
        }

        plan = self.db.find_or_create_skrap("plan", target, self.name())
        self.reconcile_meta(plan, new_meta)

    def _output_name(self, article):
        return article.name.rsplit('.', 1)[0] + '.html'

    def _article_for_output(self, target):
        for article in self.db.find_all_published_articles():
            if self._output_name(article) == target:
                return article
        return None
