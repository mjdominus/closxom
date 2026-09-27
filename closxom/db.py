
from datetime import datetime
from pathlib import Path
import logging
import sqlite3
import sys
import json

import closxom.skrap

logger = logging.getLogger("closxom.db")

class ForeignMetaWrite(Exception):
    """Raised when a save attempts to change the value of a meta key
    owned by a different plugin, or to remove one. Reads always merge
    every owner's keys into skrap.meta, so a foreign-owned key can only
    go missing at save time through an explicit del or a wholesale
    reassignment of skrap.meta - never legitimately."""
    pass

class DB():
    """Database abstraction layer for closxom.

    Provides high-level methods for managing products (skrap objects),
    plugins, and metadata.
    """

    def __init__(self, path=None):
        if path is None:
            path = self.default_path()

        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

    def default_path(self):
        return "closxom.db"

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

    # ==================== Build metadata ====================

    def record_build_time(self, now):
        """Record now (an aware datetime) as the build_time of this run."""
        self.conn.execute("INSERT INTO build (build_time) VALUES (?)", (now.isoformat(),))
        self.conn.commit()

    def get_latest_build_time(self):
        """Return the most recently recorded build_time as an aware
        datetime, or None if no build has been recorded yet."""
        c = self.conn.cursor()
        c.execute("SELECT build_time FROM build ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        return datetime.fromisoformat(row['build_time']) if row else None

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

    def _plugin_name(self, plugin_id):
        """Look up a plugin's name by its database id, or None if no
        such plugin exists."""
        c = self.conn.cursor()
        c.execute("SELECT name FROM plugin WHERE id = ?", (plugin_id,))
        row = c.fetchone()
        return row['name'] if row else None

    def _skrap_from_row(self, row):
        """Construct a Skrap object from a database row."""
        owner_name = self._plugin_name(row['owner_id']) or "unknown"

        # Create the appropriate Skrap subclass based on type
        skrap_class = closxom.skrap.get_skrap_class(row['type'])
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
        return {row['k']: self._deserialize_meta_value(row['v']) for row in c.fetchall()}

    def _serialize_meta_value(self, v):
        """Serialize compound values as JSON; store scalars as-is.
        SQLite has no boolean type, so coerce bools to 0/1."""
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        elif isinstance(v, bool):
            return int(v)
        else:
            return v

    def _deserialize_meta_value(self, v):
        """Inverse of _serialize_meta_value. Only compound values (lists,
        dicts) are JSON-encoded on save; scalars are stored as-is."""
        if isinstance(v, str) and v[:1] in ('[', '{'):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return v

    def meta_keys_owned_by(self, skrap, owner_name):
        """Return the set of meta keys currently persisted for skrap
        whose owner is owner_name. Empty if skrap is not yet saved or
        owner_name has never written a key for it.

        owner_name must already be a registered plugin - every Plugin
        registers itself in __init__, so an unregistered name here means
        a bug in the caller, not a pipeline ordering issue."""
        if skrap.id is None:
            return set()
        owner_id = self.get_plugin_id(owner_name)
        if owner_id is None:
            raise ValueError(f"{owner_name!r} is not a registered plugin")
        c = self.conn.cursor()
        c.execute("SELECT k FROM meta WHERE skrap_id = ? AND owner_id = ?",
                  (skrap.id, owner_id))
        return {row['k'] for row in c.fetchall()}

    # ==================== Skrap (product) creation and updates ====================

    def create_skrap(self, type_name, name, owner_name, meta=None, content=None):
        """Create a new skrap object and save it to the database.

        Returns the created skrap object with its database ID populated.
        """
        skrap_class = closxom.skrap.get_skrap_class(type_name)
        skrap_obj = skrap_class(name=name, owner=owner_name, meta=meta, content=content)
        self.save_skrap(skrap_obj, owner=owner_name)
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
        skrap_class = closxom.skrap.get_skrap_class(type_name)
        return skrap_class(name=name, owner=owner_name)

    def save_skrap(self, o, owner):
        """Save or update a skrap object in the database.

        owner is the name of the plugin performing this save, used to
        attribute any meta keys it adds or changes. Plugin code never
        passes this explicitly - Plugin.__init__ binds self.db to the
        plugin's own name, so self.db.save_skrap(skrap) supplies it
        automatically. Direct callers (tests, one-off scripts) must
        state it themselves.

        Meta ownership is validated before the skrap row itself is
        touched, so a ForeignMetaWrite leaves the whole save - skrap row
        included - unapplied, not just the meta rows.
        """
        o.set_last_updated()

        owner_id = self.ensure_plugin_registered(o.owner)
        meta_owner_id = self.ensure_plugin_registered(owner)
        existing_meta = self._validate_meta_ownership(o, meta_owner_id)

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

        self._write_meta(o, meta_owner_id, existing_meta)
        self.conn.commit()

        logger.info("Saved skrap %s (%r) owned by plugin %r",
                    o.id, o.name, o.owner)

        return o.id

    def _validate_meta_ownership(self, o, owner_id):
        """Check that o.meta does not change or remove any key owned by
        a plugin other than owner_id, raising ForeignMetaWrite if it
        does. Returns the current (owner_id, value) per meta key, for
        _write_meta to apply afterward - empty if o is not yet saved.
        """
        if o.id is None:
            return {}

        c = self.conn.cursor()
        c.execute("SELECT k, v, owner_id FROM meta WHERE skrap_id = ?", (o.id,))
        existing = {
            row['k']: (row['owner_id'], self._deserialize_meta_value(row['v']))
            for row in c.fetchall()
        }

        for k, (existing_owner_id, existing_v) in existing.items():
            if existing_owner_id != owner_id and (k not in o.meta or o.meta[k] != existing_v):
                owner_desc = self._plugin_name(existing_owner_id) or existing_owner_id
                raise ForeignMetaWrite(
                    f"skrap {o.id} ({o.name!r}): cannot change meta key "
                    f"{k!r}, owned by plugin {owner_desc!r}")

        return existing

    def _write_meta(self, o, owner_id, existing):
        """Apply o.meta to the meta table for owner_id, given the
        existing (owner_id, value) per key from _validate_meta_ownership.
        Assumes validation already passed: a row owned by owner_id is
        deleted if its key is absent from o.meta, or updated if o.meta's
        value for it differs; a row owned by a different plugin is left
        alone; a key in o.meta with no existing row is inserted fresh.
        """
        for k, (existing_owner_id, existing_v) in existing.items():
            if existing_owner_id != owner_id:
                continue
            if k not in o.meta:
                self.conn.execute(
                    "DELETE FROM meta WHERE skrap_id = ? AND k = ?", (o.id, k))
            elif o.meta[k] != existing_v:
                self.conn.execute(
                    "UPDATE meta SET v = ? WHERE skrap_id = ? AND k = ?",
                    (self._serialize_meta_value(o.meta[k]), o.id, k))

        for k, v in o.meta.items():
            if k not in existing:
                self.conn.execute("""
                    INSERT INTO meta (skrap_id, k, v, owner_id)
                    VALUES (?, ?, ?, ?)
                """, (o.id, k, self._serialize_meta_value(v), owner_id))
