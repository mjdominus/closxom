"""Plugin to scan filesystem for article files."""

from pathlib import Path
from cloxsom.plugin.plugin import Plugin
from cloxsom.skrap import FileSkrap


class ScanFilesPlugin(Plugin):
    """Scans the filesystem for article files and creates FileSkrap products.

    This plugin reads from the filesystem (not the database) and produces
    FileSkrap products for each file found.
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

    def run(self):
        """Scan the input directory for article files."""
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")

        # Find all files (excluding dotfiles and notyet markers)
        files_found = 0
        for path in self.input_dir.rglob("*"):
            if not path.is_file():
                continue

            # Skip dotfiles and .notyet files
            if path.name.startswith('.'):
                continue
            if path.name.endswith('.notyet'):
                continue

            # Create a FileSkrap for this file
            relpath = path.relative_to(self.input_dir)

            file_skrap = FileSkrap(
                name=str(relpath),
                owner=self.name(),
                meta={
                    'path': str(path.absolute()),
                    'relpath': str(relpath),
                    'mtime': path.stat().st_mtime
                }
            )

            self.db.save_skrap(file_skrap)
            files_found += 1

        return files_found
