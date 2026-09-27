import logging
from datetime import datetime, timezone

# abstract class for plugins

class UnimplementedMethod(Exception):
    pass

class _OwnerBoundDB():
    """Wraps a DB so that save_skrap implicitly attributes meta writes
    to the wrapped plugin's name, without every plugin having to pass
    its own name around. Reads pass straight through to the wrapped DB
    unfiltered; only save_skrap is overridden.
    """

    def __init__(self, db, owner):
        self._db = db
        self._owner = owner

    def __getattr__(self, name):
        return getattr(self._db, name)

    def save_skrap(self, skrap):
        return self._db.save_skrap(skrap, owner=self._owner)

class Plugin():
    """Base class for all plugins.

    Subclasses must implement:
    - name(): Return the plugin's unique name
    - inputs(): Return list of product types this plugin consumes
    - outputs(): Return list of product types this plugin produces
    - default_target_list(): Return list of target names to build by default
    - dependencies_of(target): Return list of skraps a target depends on
    - build_target(target): Build (and save) a single target

    run() is provided by this base class and should not normally need
    to be overridden.
    """

    @classmethod
    def name(cls):
        """Return the unique name of this plugin."""
        raise NotImplementedError(f"Plugin {cls} must implement name()")

    @classmethod
    def inputs(cls):
        """Return list of product type strings this plugin requires as input.

        Return empty list if the plugin produces products from scratch
        (e.g., scanfiles reads filesystem, not database).
        """
        raise NotImplementedError(f"Plugin {cls} must implement inputs()")

    @classmethod
    def outputs(cls):
        """Return list of product type strings this plugin produces."""
        raise NotImplementedError(f"Plugin {cls} must implement outputs()")

    def __init__(self, db, config=None, now=None):
        """Initialize plugin with database handle, shared run config, and
        with the build's frozen "now" instant.

        config is a dict of settings passed by the entry point (input_dir,
        output_dir, etc.) that any plugin may consult; unused by most.
        now is the orchestrator's frozen build time (an aware UTC
        datetime); it defaults to the current wall-clock time if not
        supplied, so a plugin instantiated directly (e.g. in a test)
        still gets a usable value.

        Registers this plugin in the database under its own name, so
        that meta_keys_owned_by(skrap, self.name()) is never asked
        about a plugin that doesn't exist yet.
        """
        db.ensure_plugin_registered(self.name())
        self.db = _OwnerBoundDB(db, self.name())
        self.config = config or {}
        self.now = now if now is not None else datetime.now(timezone.utc)
        self.log = logging.getLogger(f"closxom.plugin.{self.name()}")

    def default_target_list(self) -> list:
        """Return the list of target names to build when run() is called
        without an explicit target_list."""
        raise UnimplementedMethod(f"Plugin {self.__class__} must implement default_target_list()")

    def dependencies_of(self, target) -> list:
        """Return the list of skraps that the given target depends on."""
        raise UnimplementedMethod(f"Plugin {self.__class__} must implement dependencies_of()")

    def build_target(self, target) -> None:
        """Build (and save) the given target."""
        raise UnimplementedMethod(f"Plugin {self.__class__} must implement build_target()")

    def run(self, target_list=None, options=None):
        """Build each target in target_list, skipping any that are already
        up to date.

        target_list defaults to self.default_target_list(). options
        defaults to {}.

        For each target, if it does not already exist, build_target(target)
        is called. Otherwise, the target's dependencies (from
        dependencies_of(target)) are compared against the target's own
        last_updated time; if any dependency is newer, the target is stale
        and build_target(target) is called again. Otherwise the target is
        skipped.
        """
        if target_list is None:
            target_list = self.default_target_list()
        if options is None:
            options = {}

        for target in target_list:
            existing = self.db.find_skrap_by_name(self.name(), target)

            if existing is None:
                self.log.info("Building target %r: does not exist yet", target)
                self.build_target(target)
                continue

            deps = self.dependencies_of(target)
            stale_deps = [dep for dep in deps if dep.last_updated >= existing.last_updated]

            if stale_deps:
                self.log.info(
                    "Rebuilding target %r: dependencies changed: %s",
                    target, ", ".join(str(dep) for dep in stale_deps),
                )
                self.build_target(target)
            else:
                self.log.info("Skipping target %r: up to date", target)

    def update_skrap_meta(self, skrap, **kwargs):
        """Set one or more meta keys on skrap, saving it only if a value
        actually changed.

        For each key=value pair, the key counts as changed if it is
        absent from skrap.meta or its current value differs. If any key
        changed, skrap.meta is updated and the skrap is saved. Bools are
        normalized to 0/1 first, since that is how the meta store holds
        them. Returns True if a save occurred, False otherwise.
        """
        changed = False
        for key, value in kwargs.items():
            if isinstance(value, bool):
                value = int(value)
            if key not in skrap.meta or skrap.meta[key] != value:
                skrap.meta[key] = value
                changed = True
        if changed:
            self.db.save_skrap(skrap)
        return changed

    def set_skrap_meta_defaults(self, skrap, **kwargs):
        """Set meta keys on skrap only where they are currently absent,
        analogous to dict.setdefault, saving it only if a key was added.

        Keys already present in skrap.meta are left untouched, whatever
        their value. Bools are normalized to 0/1. Returns True if a save
        occurred, False otherwise.
        """
        changed = False
        for key, value in kwargs.items():
            if key not in skrap.meta:
                if isinstance(value, bool):
                    value = int(value)
                skrap.meta[key] = value
                changed = True
        if changed:
            self.db.save_skrap(skrap)
        return changed

    def reconcile_meta(self, skrap, new_dict):
        """Replace this plugin's previously authored meta keys on skrap
        with new_dict: every key in new_dict is set (added or
        overwritten), and any key this plugin owned before but that is
        absent from new_dict is removed. Keys owned by other plugins are
        never touched. Saves only if something changed. Returns True if
        a save occurred, False otherwise.
        """
        owned = self.db.meta_keys_owned_by(skrap, self.name())
        to_delete = owned - new_dict.keys()

        changed = bool(to_delete) or any(
            skrap.meta.get(k) != v for k, v in new_dict.items())

        for k in to_delete:
            del skrap.meta[k]
        skrap.meta.update(new_dict)

        if changed:
            self.db.save_skrap(skrap)
        return changed

    def __str__(self):
        return f"<plugin {self.name()}>"

    def __repr__(self):
        return self.__str__()

# This should be in the test suite, not here
# But I don't want to figure out pytest right now
class TestPlugin(Plugin):
    @classmethod
    def typ(cls):
        return "test plugin"
