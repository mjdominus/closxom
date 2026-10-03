"""Plugin to write HTML output files from PlanSkraps."""

from datetime import datetime
from html import escape as escape_html
from pathlib import Path

from closxom.plugin.base import Plugin


class WriteHtmlPlugin(Plugin):
    """Executes each PlanSkrap: fills its named template with its values
    and the content of the skraps listed in built_from, then writes the
    result to output_path.

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
        values = plan.meta.get('values', {})
        title = values.get('title', 'Untitled')
        pubdate = values.get('pubdate')

        date_html = ''
        if pubdate:
            dt = datetime.fromisoformat(pubdate)
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
{self.built_from_content(plan)}
        </div>
    </article>
</body>
</html>"""

    def built_from_content(self, plan):
        """Concatenate the already-rendered content of every skrap
        listed in built_from - never re-escaped, it's HTML already."""
        parts = []
        for ref in plan.meta.get('built_from', []):
            skrap = self.db.find_skrap_by_name(ref['owner'], ref['name'])
            if skrap is not None and skrap.content:
                parts.append(skrap.content)
        return '\n'.join(parts)
