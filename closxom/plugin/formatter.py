"""Plugin to render an article's body to HTML."""

import mistune

from closxom.plugin.base import Plugin


class FormatterPlugin(Plugin):
    """Creates or updates one HTMLSkrap per ArticleSkrap, rendering its
    body according to its `formatter:` META key.

    formatter:      action
    absent          render as Markdown (the default)
    markdown        render as Markdown
    raw             pass the body through unchanged (already HTML)
    anything else   fail_article - not a recognized formatter
    """

    @classmethod
    def name(cls):
        return "formatter"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return ["html"]

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

        formatter = article.meta.get('formatter', 'markdown')
        if formatter == 'markdown':
            rendered = mistune.html(article.content or '')
        elif formatter == 'raw':
            rendered = article.content or ''
        else:
            self.fail_article(article, f"unrecognized formatter: {formatter!r}")

        html_skrap = self.db.find_or_create_skrap("html", target, self.name())
        old_content = html_skrap.content
        html_skrap.content = rendered
        if html_skrap.content != old_content:
            self.db.save_skrap(html_skrap)
