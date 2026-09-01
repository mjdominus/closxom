
from pathlib import Path
import logging
import sqlite3
import sys
import json

import cloxsom.skrap

logger = logging.getLogger("cloxsom.db")

class DB():
    """Database abstraction layer for cloxsom.

    Provides high-level methods for managing products (skrap objects),
    plugins, and metadata.
    """

    def __init__(self, path=None):
        if path is None:
            path = self.default_path()

        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

    def default_path(self):
        return "cloxsom.db"

    def create_tables(self, d=None):
        if d is None:
            d=Path("SCHEMA")
        for f in d.glob("*.sql"):
            table = f.stem
            print(f"creating table {table}", file=sys.stderr)
            sql = f.read_text()
            self.conn.execute(sql)
        self.conn.commit()

    # ==================== Plugin management ====================

    def ensure_plugin_registered(self, plugin_name):
        """Ensure a plugin is registered in the database."""
        c = self.conn.cursor()
        c.execute("SELECT id FROM plugin WHERE name = ?", (plugin_name,))
        row = c.fetchone()

        if row is None:
            c.execute("INSERT INTO plugin (name) VALUES (?)", (plugin_name,))
            self.conn.commit()
            c.execute("SELECT id FROM plugin WHERE name = ?", (plugin_name,))
            row = c.fetchone()

        return row['id']

    def get_plugin_id(self, plugin_name):
        """Get the database ID for a plugin by name."""
        c = self.conn.cursor()
        c.execute("SELECT id FROM plugin WHERE name = ?", (plugin_name,))
        row = c.fetchone()
        return row['id'] if row else None

    # ==================== Skrap (product) queries ====================

    def find_skrap_by_id(self, id):
        """Find a skrap by its database ID."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM skrap WHERE id = ?", (id, ))
        rec = c.fetchone()
        if rec is None:
            return None
        return self._skrap_from_row(rec)

    def find_skrap_by_name(self, owner_name, name):
        """Find a skrap by owner plugin name and skrap name."""
        owner_id = self.get_plugin_id(owner_name)
        if owner_id is None:
            return None

        c = self.conn.cursor()
        c.execute("SELECT * FROM skrap WHERE owner_id = ? AND name = ?",
                  (owner_id, name))
        rec = c.fetchone()
        if rec is None:
            return None
        return self._skrap_from_row(rec)

    def find_all_skrap_by_type(self, type_name):
        """Find all skrap objects of a given type.

        Returns a list of skrap objects.
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM skrap WHERE type = ?", (type_name,))
        return [self._skrap_from_row(row) for row in c.fetchall()]

    def find_all_skrap_by_owner(self, owner_name):
        """Find all skrap objects owned by a given plugin.

        Returns a list of skrap objects.
        """
        owner_id = self.get_plugin_id(owner_name)
        if owner_id is None:
            return []

        c = self.conn.cursor()
        c.execute("SELECT * FROM skrap WHERE owner_id = ?", (owner_id,))
        return [self._skrap_from_row(row) for row in c.fetchall()]

    def find_all_skrap(self):
        """Find all skrap objects in the database."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM skrap")
        return [self._skrap_from_row(row) for row in c.fetchall()]

    def find_all_published_articles(self):
        """Find all published article skrap objects."""
        return [art for art in self.find_all_skrap_by_type('article') if art.is_published()]

    def _skrap_from_row(self, row):
        """Construct a Skrap object from a database row."""
        # Get the plugin name from the owner_id
        c = self.conn.cursor()
        c.execute("SELECT name FROM plugin WHERE id = ?", (row['owner_id'],))
        plugin_row = c.fetchone()
        owner_name = plugin_row['name'] if plugin_row else "unknown"

        # Create the appropriate Skrap subclass based on type
        skrap_class = cloxsom.skrap.get_skrap_class(row['type'])
        skrap_obj = skrap_class(
            name=row['name'],
            owner=owner_name,
            last_updated=row['last_updated'],
            id=row['id'],
            content=row['content']
        )

        # Load metadata
        skrap_obj.meta = self._load_metadata(row['id'])

        return skrap_obj

    def _load_metadata(self, skrap_id):
        """Load all metadata for a skrap object."""
        c = self.conn.cursor()
        c.execute("SELECT k, v FROM meta WHERE skrap_id = ?", (skrap_id,))
        meta = {}
        for row in c.fetchall():
            # Try to deserialize JSON values, fall back to raw string
            try:
                meta[row['k']] = json.loads(row['v'])
            except (json.JSONDecodeError, TypeError):
                meta[row['k']] = row['v']
        return meta

    # ==================== Skrap (product) creation and updates ====================

    def create_skrap(self, type_name, name, owner_name, meta=None, content=None):
        """Create a new skrap object and save it to the database.

        Returns the created skrap object with its database ID populated.
        """
        skrap_class = cloxsom.skrap.get_skrap_class(type_name)
        skrap_obj = skrap_class(name=name, owner=owner_name, meta=meta, content=content)
        self.save_skrap(skrap_obj)
        return skrap_obj

    def find_or_create_skrap(self, type_name, name, owner_name):
        """Find an existing skrap by (owner_name, name), or construct a
        new, not-yet-saved one of the given type if none exists.

        Does not save - callers should set whatever meta/content they
        need and then call save_skrap().
        """
        existing = self.find_skrap_by_name(owner_name, name)
        if existing is not None:
            return existing
        skrap_class = cloxsom.skrap.get_skrap_class(type_name)
        return skrap_class(name=name, owner=owner_name)

    def save_skrap(self, o):
        """Save or update a skrap object in the database."""
        import time
        o.set_last_updated()

        # Ensure owner plugin is registered
        owner_id = self.ensure_plugin_registered(o.owner)

        if o.id is None:
            # Insert new skrap
            self.conn.execute("""
                INSERT INTO skrap(name, type, owner_id, last_updated, content)
                VALUES (?, ?, ?, ?, ?)
            """, (o.name, o.type, owner_id, o.last_updated, o.content))
            c = self.conn.cursor()
            c.execute("""
                SELECT id FROM skrap
                WHERE name = ? AND owner_id = ?
            """, (o.name, owner_id))
            o.id = c.fetchone()['id']
        else:
            # Update existing skrap
            self.conn.execute("""
                UPDATE skrap SET name = ?, type = ?, owner_id = ?, last_updated = ?, content = ?
                WHERE id = ?
            """, (o.name, o.type, owner_id, o.last_updated, o.content, o.id))

        self.save_skrap_metadata(o)
        self.conn.commit()

        logger.info("Saved skrap %s (%r) owned by plugin %r",
                    o.id, o.name, o.owner)

        return o.id

    def save_skrap_metadata(self, o):
        """Save metadata for a skrap object."""
        if o.id is None:
            raise Exception("Cannot save metadata for skrap without ID")

        # Delete existing metadata
        self.conn.execute("DELETE FROM meta WHERE skrap_id = ?", (o.id,))

        # Insert new metadata
        for k, v in o.meta.items():
            # Serialize complex values as JSON
            if isinstance(v, (dict, list)):
                v_serialized = json.dumps(v)
            else:
                v_serialized = v

            self.conn.execute("""
                INSERT INTO meta (skrap_id, k, v)
                VALUES (?, ?, ?)
            """, (o.id, k, v_serialized))

        self.conn.commit()
