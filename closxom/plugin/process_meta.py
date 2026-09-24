"""Plugin to parse META sections from articles."""

import re
from closxom.plugin.base import Plugin


class ProcessMetaPlugin(Plugin):
    """Parses META sections from article content.

    Processes ArticleSkrap products, extracting META headers and
    separating them from the content. Updates articles in place.
    """

    @classmethod
    def name(cls):
        return "process-meta"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return []  # Modifies articles in place

    def run(self):
        """Parse META sections from all articles."""
        articles = self.db.find_all_skrap_by_type("article")

        processed = 0
        for article in articles:
            content = article.content or ''

            # Check if content starts with META
            if content.startswith('META\n'):
                meta_dict, body = self.parse_meta(content)

                # 'published' is a distinct key from the resolver's derived
                # 'pubdate'/'published' (see notes/redesign-decisions.md,
                # "Meta key provenance": one writer per key). Reconciled
                # explicitly (rather than via .update()) so deleting the
                # published: line from the source file actually clears a
                # stale value, which is how an article is unpublished.
                if 'published' in meta_dict:
                    article.meta['published_raw'] = meta_dict.pop('published')
                else:
                    article.meta.pop('published_raw', None)

                # Update article metadata
                article.meta.update(meta_dict)
                article.content = body

                # If no title was found in META, use first line of body
                if 'title' not in article.meta and body:
                    first_line = body.split('\n', 1)[0].strip()
                    if first_line:
                        article.meta['title'] = first_line

            else:
                # No META section - use first line as title
                first_line = content.split('\n', 1)[0].strip() if content else 'Untitled'
                article.meta['title'] = first_line

            self.db.save_skrap(article)
            processed += 1

        return processed

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
