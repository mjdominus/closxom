"""Plugin to plan a year-archive output page aggregating every published
article from that year."""

from datetime import datetime

from closxom.plugin.base import Plugin


class PlanYearArchivePagePlugin(Plugin):
    """Creates or updates one PlanSkrap per year that has (or had) a
    published article, aggregating every such article into one archive
    page. Named after its output file (e.g. `2027/index.html`), not any
    input file - see PlanSkrap's docstring. Uses the 'archive' template,
    the same one month/day archives will use later - the template only
    needs a page title and a list of articles, with no notion of what
    kind of archive it is.
    """

    @classmethod
    def name(cls):
        return "plan-year-archive-page"

    @classmethod
    def inputs(cls):
        return ["article", "publication", "html"]

    @classmethod
    def outputs(cls):
        return ["plan"]

    def default_target_list(self):
        # Every year with a currently-published article, plus every year
        # this plugin already has a plan for - so a year that loses all
        # its articles still gets revisited (see lt yhhrg5) rather than
        # silently dropping out of the list.
        derived = {self._output_name(year) for year in self._years_with_published_articles()}
        existing = {p.name for p in self.db.find_all_skrap_by_type("plan")
                    if p.owner == self.name()}
        return sorted(derived | existing)

    def dependencies_of(self, target):
        deps = []
        for article, publication, html in self._articles_in_year(self._year_for_output(target)):
            deps.append(article)
            if publication is not None:
                deps.append(publication)
            deps.append(html)
        return deps

    def build_target(self, target):
        year = self._year_for_output(target)
        contributors = self._articles_in_year(year)
        if not contributors:
            # No currently-published article for this year - leave any
            # existing plan/output alone. What should actually happen
            # here (delete the plan? mark it empty?) is still open, see
            # lt yhhrg5.
            self.log.warning("No published articles for year %r; leaving any "
                              "existing plan untouched", year)
            return

        article_values = []
        built_from = []
        for article, publication, html in contributors:
            article_values.append({
                'title': article.meta.get('title', '(no title)'),
                'date': publication.meta.get('pubdate') if publication else None,
                'content': html.content or '',
                'url': self._article_output_name(article),
            })
            built_from.append({'owner': 'formatter', 'name': article.name})

        new_meta = {
            'template': 'archive',
            'values': {
                'title': f"Articles from {year}",
                'articles': article_values,
            },
            'built_from': built_from,
            'output_path': target,
        }

        plan = self.db.find_or_create_skrap("plan", target, self.name())
        self.reconcile_meta(plan, new_meta)

    def _output_name(self, year):
        return f"{year}/index.html"

    def _year_for_output(self, target):
        return int(target.split('/', 1)[0])

    def _article_output_name(self, article):
        return article.name.rsplit('.', 1)[0] + '.html'

    def _pubdate_of(self, article):
        publication = self.db.find_skrap_by_name("resolve-publication", article.name)
        return publication, (publication.meta.get('pubdate') if publication else None)

    def _years_with_published_articles(self):
        years = set()
        for article in self.db.find_all_published_articles():
            _, pubdate = self._pubdate_of(article)
            if pubdate is not None:
                years.add(datetime.fromisoformat(pubdate).year)
        return years

    def _articles_in_year(self, year):
        """Every published article whose pubdate falls in year, paired
        with its publication and html skraps, newest first."""
        result = []
        for article in self.db.find_all_published_articles():
            publication, pubdate = self._pubdate_of(article)
            if pubdate is None or datetime.fromisoformat(pubdate).year != year:
                continue
            html = self.db.find_skrap_by_name("formatter", article.name)
            if html is None:
                self.log.warning("No rendered HTML for %r yet", article.name)
                continue
            result.append((article, publication, html))
        result.sort(key=lambda triple: triple[1].meta.get('pubdate') or '', reverse=True)
        return result
