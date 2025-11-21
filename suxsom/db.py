
from pathlib import Path
import sqlite3
import sys
import json

import suxsom.sux

class DB():
    """Database abstraction layer for suxsom.

    Provides high-level methods for managing products (sux objects),
    plugins, and metadata.
    """

    def __init__(self, path=None):
        if path is None:
            path = self.default_path()

        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

    def default_path(self):
        return "suxsom.db"

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

    # ==================== Sux (product) queries ====================

    def find_sux_by_id(self, id):
        """Find a sux by its database ID."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM sux WHERE id = ?", (id, ))
        rec = c.fetchone()
        if rec is None:
            return None
        return self._sux_from_row(rec)

    def find_sux_by_name(self, owner_name, name):
        """Find a sux by owner plugin name and sux name."""
        owner_id = self.get_plugin_id(owner_name)
        if owner_id is None:
            return None

        c = self.conn.cursor()
        c.execute("SELECT * FROM sux WHERE owner_id = ? AND name = ?",
                  (owner_id, name))
        rec = c.fetchone()
        if rec is None:
            return None
        return self._sux_from_row(rec)

    def find_all_sux_by_type(self, type_name):
        """Find all sux objects of a given type.

        Returns a list of sux objects.
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM sux WHERE type = ?", (type_name,))
        return [self._sux_from_row(row) for row in c.fetchall()]

    def find_all_sux_by_owner(self, owner_name):
        """Find all sux objects owned by a given plugin.

        Returns a list of sux objects.
        """
        owner_id = self.get_plugin_id(owner_name)
        if owner_id is None:
            return []

        c = self.conn.cursor()
        c.execute("SELECT * FROM sux WHERE owner_id = ?", (owner_id,))
        return [self._sux_from_row(row) for row in c.fetchall()]

    def find_all_sux(self):
        """Find all sux objects in the database."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM sux")
        return [self._sux_from_row(row) for row in c.fetchall()]

    def _sux_from_row(self, row):
        """Construct a Sux object from a database row."""
        # Get the plugin name from the owner_id
        c = self.conn.cursor()
        c.execute("SELECT name FROM plugin WHERE id = ?", (row['owner_id'],))
        plugin_row = c.fetchone()
        owner_name = plugin_row['name'] if plugin_row else "unknown"

        # Create the appropriate Sux subclass based on type
        sux_class = suxsom.sux.get_sux_class(row['type'])
        sux_obj = sux_class(
            name=row['name'],
            owner=owner_name,
            last_modified=row['last_modified'],
            id=row['id']
        )

        # Load metadata
        sux_obj.meta = self._load_metadata(row['id'])

        return sux_obj

    def _load_metadata(self, sux_id):
        """Load all metadata for a sux object."""
        c = self.conn.cursor()
        c.execute("SELECT k, v FROM meta WHERE sux_id = ?", (sux_id,))
        meta = {}
        for row in c.fetchall():
            # Try to deserialize JSON values, fall back to raw string
            try:
                meta[row['k']] = json.loads(row['v'])
            except (json.JSONDecodeError, TypeError):
                meta[row['k']] = row['v']
        return meta

    # ==================== Sux (product) creation and updates ====================

    def create_sux(self, type_name, name, owner_name, meta=None):
        """Create a new sux object and save it to the database.

        Returns the created sux object with its database ID populated.
        """
        sux_class = suxsom.sux.get_sux_class(type_name)
        sux_obj = sux_class(name=name, owner=owner_name, meta=meta)
        self.save_sux(sux_obj)
        return sux_obj

    def save_sux(self, o):
        """Save or update a sux object in the database."""
        import time
        o.set_last_modified()

        # Ensure owner plugin is registered
        owner_id = self.ensure_plugin_registered(o.owner)

        if o.id is None:
            # Insert new sux
            self.conn.execute("""
                INSERT INTO sux(name, type, owner_id, last_modified)
                VALUES (?, ?, ?, ?)
            """, (o.name, o.type, owner_id, o.last_modified))
            c = self.conn.cursor()
            c.execute("""
                SELECT id FROM sux
                WHERE name = ? AND owner_id = ?
            """, (o.name, owner_id))
            o.id = c.fetchone()['id']
        else:
            # Update existing sux
            self.conn.execute("""
                UPDATE sux SET name = ?, type = ?, owner_id = ?, last_modified = ?
                WHERE id = ?
            """, (o.name, o.type, owner_id, o.last_modified, o.id))

        self.save_sux_metadata(o)
        self.conn.commit()

        return o.id

    def save_sux_metadata(self, o):
        """Save metadata for a sux object."""
        if o.id is None:
            raise Exception("Cannot save metadata for sux without ID")

        # Delete existing metadata
        self.conn.execute("DELETE FROM meta WHERE sux_id = ?", (o.id,))

        # Insert new metadata
        for k, v in o.meta.items():
            # Serialize complex values as JSON
            if isinstance(v, (dict, list)):
                v_serialized = json.dumps(v)
            else:
                v_serialized = v

            self.conn.execute("""
                INSERT INTO meta (sux_id, k, v)
                VALUES (?, ?, ?)
            """, (o.id, k, v_serialized))

        self.conn.commit()
