"""Plugin to copy file contents into ArticleSkrap products."""

from closxom.plugin.base import Plugin


class ReadFilesPlugin(Plugin):
    """Copies FileSkrap content into ArticleSkrap products.

    Consumes FileSkrap products, whose content scanfiles has already
    loaded, and produces one ArticleSkrap per file holding a pristine
    copy of that content. Does not touch the filesystem.
    """

    @classmethod
    def name(cls):
        return "readfiles"

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

        wanted_meta = {
            k: file_skrap.meta[k]
            for k in ("path", "relpath", "file_mtime")
            if k in file_skrap.meta
        }

        if (article.id is not None
                and article.content == file_skrap.content
                and all(article.meta.get(k) == v for k, v in wanted_meta.items())):
            self.log.info("Skipping target %r: article already current", target)
            return

        article.content = file_skrap.content
        article.meta.update(wanted_meta)
        self.db.save_skrap(article)
