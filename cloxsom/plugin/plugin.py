import logging

# abstract class for plugins

class Plugin():
    """Base class for all plugins.

    Subclasses must implement:
    - name(): Return the plugin's unique name
    - inputs(): Return list of product types this plugin consumes
    - outputs(): Return list of product types this plugin produces
    - run(): Execute the plugin's main logic
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

    def __init__(self, db):
        """Initialize plugin with database handle."""
        self.db = db
        self.log = logging.getLogger(f"cloxsom.plugin.{self.name()}")

    def run(self):
        """Execute the plugin's main logic.

        This method should query the database for input products,
        process them, and create new output products.
        """
        raise NotImplementedError(f"Plugin {self.__class__} must implement run()")

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
