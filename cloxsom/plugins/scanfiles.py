"""Plugin to scan filesystem for article files."""

from pathlib import Path
from cloxsom.plugin.plugin import Plugin


class ScanFilesPlugin(Plugin):
    """Scans the filesystem for article files and creates FileSkrap products.

    This plugin reads from the filesystem (not the database) and produces
    FileSkrap products for each file found.

    Overrides run() directly rather than using the base class's target/
    dependency machinery: staleness here means comparing a raw file mtime
    against FileSkrap.meta['file_mtime'], not comparing one skrap's
    last_updated against another's.
    """

    @classmethod
    def name(cls):
        return "scanfiles"

    @classmethod
    def inputs(cls):
        return []  # Reads from filesystem, not database

    @classmethod
    def outputs(cls):
        return ["file"]

    def __init__(self, db, config=None):
        """Initialize the scanfiles plugin.

        Reads config['input_dir'] (defaults to 'articles').
        """
        super().__init__(db, config)
        self.input_dir = Path(self.config.get('input_dir') or "articles")

    def run(self, target_list=None, options=None):
        """Scan the input directory for article files."""
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")

        # Find all files (excluding dotfiles and notyet markers)
        files_updated = 0
        for path in self.input_dir.rglob("*"):
            if not path.is_file():
                continue

            # Skip dotfiles and .notyet files
            if path.name.startswith('.'):
                continue
            if path.name.endswith('.notyet'):
                continue

            relpath = path.relative_to(self.input_dir)
            mtime = path.stat().st_mtime
            notyet_path = path.parent / (path.name + '.notyet')
            has_notyet = notyet_path.exists()

            # Update the existing FileSkrap in place if one already exists
            # for this name, rather than trying to insert a second row and
            # hitting the UNIQUE(name, owner_id) constraint.
            file_skrap = self.db.find_or_create_skrap("file", str(relpath), self.name())
            is_new = file_skrap.id is None

            if not is_new and (
                    file_skrap.meta.get('file_mtime') == mtime and
                    file_skrap.meta.get('has_notyet') == has_notyet):
                self.log.info("Skipping %r: unchanged", str(relpath))
                continue

            self.log.info("Found new file %r" if is_new else "File %r changed", str(relpath))

            try:
                content = path.read_text(encoding='utf-8')
            except OSError as e:
                self.log.warning("Could not read %s: %s", path, e)
                continue

            file_skrap.content = content
            file_skrap.meta.update({
                'path': str(path.absolute()),
                'relpath': str(relpath),
                'file_mtime': mtime,
                'has_notyet': has_notyet,
            })

            self.db.save_skrap(file_skrap)
            files_updated += 1

        return files_updated
