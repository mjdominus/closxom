"""Plugin to filter out unpublished articles."""

from closxom.plugin.plugin import Plugin


class NotYetPlugin(Plugin):
    """Marks articles as unpublished if they have a .notyet file.

    Modifies existing ArticleSkrap products in place, setting their
    'published' metadata to False if scanfiles saw a .notyet marker for
    the corresponding file. Reads FileSkrap.meta['has_notyet'] rather
    than stat'ing the filesystem itself - only scanfiles does that.
    """

    @classmethod
    def name(cls):
        return "notyet"

    @classmethod
    def inputs(cls):
        return ["article"]

    @classmethod
    def outputs(cls):
        return []  # Modifies articles in place, doesn't create new products

    def run(self):
        """Check FileSkrap.meta['has_notyet'] and mark articles as unpublished."""
        articles = self.db.find_all_skrap_by_type("article")

        marked_unpublished = 0
        for article in articles:
            file_skrap = self.db.find_skrap_by_name("scanfiles", article.name)
            has_notyet = bool(file_skrap and file_skrap.meta.get('has_notyet'))

            if has_notyet:
                if self.update_skrap_meta(article, published=False):
                    marked_unpublished += 1
            else:
                # Default to published if not specified
                self.set_skrap_meta_defaults(article, published=True)

        return marked_unpublished
