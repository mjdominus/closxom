"""Plugin to scan filesystem for article files."""

from pathlib import Path
from suxsom.plugin.plugin import Plugin
from suxsom.sux import FileSux


class ScanFilesPlugin(Plugin):
    """Scans the filesystem for article files and creates FileSux products.

    This plugin reads from the filesystem (not the database) and produces
    FileSux products for each file found.
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

    def __init__(self, db, input_dir=None):
        """Initialize the scanfiles plugin.

        Args:
            db: Database handle
            input_dir: Directory to scan (defaults to 'articles')
        """
        super().__init__(db)
        self.input_dir = Path(input_dir) if input_dir else Path("articles")

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

            # Create a FileSux for this file
            relpath = path.relative_to(self.input_dir)

            file_sux = FileSux(
                name=str(relpath),
                owner=self.name(),
                meta={
                    'path': str(path.absolute()),
                    'relpath': str(relpath),
                    'mtime': path.stat().st_mtime
                }
            )

            self.db.save_sux(file_sux)
            files_found += 1

        return files_found
