"""Plugin to create/update ArticleSkrap products from FileSkrap sources."""

import re
from closxom.plugin.base import Plugin


class ProcessMetaPlugin(Plugin):
    """Creates or updates one ArticleSkrap per FileSkrap, generating it
    directly from the file's raw content rather than copying it in one
    pass and mutating it in a later one.

    An article's name always equals its source file's relpath, so the
    FileSkrap found by (owner="scanfiles", name=target) is its one
    dependency - no separate path/relpath/file_mtime bookkeeping is kept
    on the article; downstream consumers use the article's own name.

    Parses the leading META section into meta via reconcile_meta and
    leaves article.content as the body only - never the raw,
    META-prefixed source. Every article is expected to have a META
    section by the time it reaches Closxom (b2c normalizes any that
    lack one); a missing META section, or one with no title:, fails the
    article via Plugin.fail_article.
    """

    @classmethod
    def name(cls):
        return "process-meta"

    @classmethod
    def inputs(cls):
        return ["file"]

    @classmethod
    def outputs(cls):
        return ["article"]

    def default_target_list(self):
        return [f.name for f in self.db.find_all_skrap_by_type("file")]

    def dependencies_of(self, target):
        file_skrap = self.db.find_skrap_by_name("scanfiles", target)
        return [file_skrap] if file_skrap else []

    def build_target(self, target):
        file_skrap = self.db.find_skrap_by_name("scanfiles", target)
        if file_skrap is None:
            self.log.warning("No file skrap for target %r", target)
            return

        if file_skrap.content is None:
            self.log.warning("File skrap %r has no content; skipping", target)
            return

        article = self.db.find_or_create_skrap("article", target, self.name())
        old_content = article.content
        raw = file_skrap.content

        # Every article has a META section by the time it reaches Closxom
        # (b2c normalizes any that lack one) - see notes/redesign-decisions.md,
        # "Articles with no META section".
        if not raw.startswith('META\n'):
            self.fail_article(article, "no META section found")

        meta_dict, body = self.parse_meta(raw)

        # 'published' is a distinct key from the resolver's derived
        # 'pubdate'/'published' (see notes/redesign-decisions.md,
        # "Meta key provenance": one writer per key).
        if 'published' in meta_dict:
            meta_dict['published_raw'] = meta_dict.pop('published')

        if 'title' not in meta_dict:
            self.fail_article(article, "META section has no title:")

        article.content = body

        # reconcile_meta reconciles process-meta's own authored keys
        # (adding, updating, and deleting exactly what changed) and
        # saves iff they did; a body edit with no META change still
        # needs its own save.
        meta_changed = self.reconcile_meta(article, meta_dict)
        if article.content != old_content and not meta_changed:
            self.db.save_skrap(article)

    def parse_meta(self, content):
        """Parse META section from content.

        Returns:
            Tuple of (meta_dict, body_content)
        """
        lines = content.split('\n')
        meta_dict = {}
        i = 1  # Skip 'META' line

        # Parse META headers
        while i < len(lines):
            line = lines[i]

            # Empty line ends META section
            if not line.strip():
                i += 1
                break

            # Parse key: value
            match = re.match(r'^([A-Za-z][-A-Za-z0-9_]*)\s*:\s*(.*)$', line)
            if match:
                key, value = match.groups()
                meta_dict[key.lower()] = value.strip()
            else:
                # Malformed META line, treat as end of META
                # TODO : diagnose error
                break

            i += 1

        # Rest is body content
        body = '\n'.join(lines[i:])

        return meta_dict, body
