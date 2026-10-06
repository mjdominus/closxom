"""Plugin to write HTML output files from PlanSkraps."""

from datetime import datetime
from html import escape as escape_html
from pathlib import Path

from closxom.plugin.base import Plugin


class WriteHtmlPlugin(Plugin):
    """Executes each PlanSkrap: fills its named template with its
    values, then writes the result to output_path. built_from is not
    consulted here - values already carries everything the template
    needs, fully resolved by the planner.

    Overrides run() directly rather than using the base class's target/
    dependency machinery: staleness here means comparing a PlanSkrap's
    last_updated against the output file's own mtime on disk, not one
    skrap's last_updated against another's - the same kind of
    filesystem-boundary override scanfiles uses, just in the opposite
    direction (writing out instead of reading in). No tracking skrap is
    needed; the output file's own mtime already is the record.
    """

    @classmethod
    def name(cls):
        return "write-html"

    @classmethod
    def inputs(cls):
        return ["plan"]

    @classmethod
    def outputs(cls):
        return []  # Writes to filesystem

    def __init__(self, db, config=None, now=None):
        """Initialize the HTML writer.

        Reads config['output_dir'] (defaults to 'output').
        """
        super().__init__(db, config, now=now)
        self.output_dir = Path(self.config.get('output_dir') or "output")

    def default_target_list(self):
        return [p.name for p in self.db.find_all_skrap_by_type("plan")]

    def run(self, target_list=None, options=None):
        """Write HTML files for every plan whose output is stale."""
        if target_list is None:
            target_list = self.default_target_list()

        # Plans may be owned by any planner (plan-article-page today,
        # others later), so look them up by name within the type - not
        # by (owner, name), since write-html isn't their owner.
        plans_by_name = {p.name: p for p in self.db.find_all_skrap_by_type("plan")}

        files_written = 0
        for target in target_list:
            plan = plans_by_name.get(target)
            if plan is None:
                self.log.warning("No plan skrap for target %r", target)
                continue

            output_path = self.output_dir / plan.meta['output_path']

            if output_path.exists() and output_path.stat().st_mtime >= plan.last_updated:
                self.log.info("Skipping %r: output is up to date", plan.name)
                continue

            html = self.render(plan)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            files_written += 1

        return files_written

    def render(self, plan):
        """Render a plan's template. Only 'single_article' exists so far."""
        template = plan.meta.get('template')
        if template == 'single_article':
            return self.render_single_article(plan)
        raise ValueError(f"Plan {plan.name!r}: unknown template {template!r}")

    def render_single_article(self, plan):
        articles = plan.meta.get('values', {}).get('articles', [{}])
        if len(articles) > 1:
            self.log.warning(
                "Plan %r: template 'single_article' expects one article, got %d; "
                "using the first", plan.name, len(articles))
        article = articles[0]
        title = article.get('title', '(no title)')
        date = article.get('date')
        content = article.get('content', '')

        date_html = ''
        if date:
            dt = datetime.fromisoformat(date)
            date_html = f"<p class='date'>{dt.strftime('%B %d, %Y')}</p>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{escape_html(title)}</title>
</head>
<body>
    <article>
        <h1>{escape_html(title)}</h1>
        {date_html}
        <div class='content'>
{content}
        </div>
    </article>
</body>
</html>"""
