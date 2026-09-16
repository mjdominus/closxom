"""Plugin orchestration system with dependency resolution."""

import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import List, Set, Dict, Type


class PluginOrchestrator:
    """Orchestrates plugin execution based on dependency resolution.

    Plugins declare what product types they consume (inputs) and produce (outputs).
    The orchestrator builds a dependency graph and executes plugins in the correct order.
    """

    def __init__(self, db, config=None, now=None):
        """now is the frozen build time (an aware UTC datetime) handed to
        every plugin this orchestrator runs; defaults to the current
        wall-clock time. Recorded to the DB once, at the start of run()."""
        self.db = db
        self.config = config or {}
        self.now = now if now is not None else datetime.now(timezone.utc)
        self.plugins: List[Type] = []
        self.plugin_instances: Dict[str, object] = {}

    def register(self, plugin_class):
        """Register a plugin class for execution."""
        self.plugins.append(plugin_class)
        return self

    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build a dependency graph based on plugin inputs/outputs.

        Returns a dict mapping plugin names to the set of plugins they depend on.
        A plugin depends on another if it consumes types that the other produces.
        """
        # Map product types to the plugins that produce them
        producers: Dict[str, Set[str]] = defaultdict(set)

        for plugin_class in self.plugins:
            plugin_name = plugin_class.name()
            outputs = plugin_class.outputs()
            for output_type in outputs:
                producers[output_type].add(plugin_name)

        # Build dependency graph
        dependencies: Dict[str, Set[str]] = defaultdict(set)

        for plugin_class in self.plugins:
            plugin_name = plugin_class.name()
            inputs = plugin_class.inputs()

            # This plugin depends on all plugins that produce its required inputs
            for input_type in inputs:
                if input_type in producers:
                    dependencies[plugin_name].update(producers[input_type])

        return dependencies

    def topological_sort(self) -> List[str]:
        """Perform topological sort to determine plugin execution order.

        Returns a list of plugin names in execution order.
        Raises an exception if circular dependencies are detected.
        """
        dependencies = self.build_dependency_graph()
        plugin_names = [p.name() for p in self.plugins]

        # Calculate in-degrees
        in_degree = {name: 0 for name in plugin_names}
        for name in plugin_names:
            for dep in dependencies[name]:
                if dep in in_degree:  # Only count dependencies that are registered
                    in_degree[name] += 1

        # Queue of plugins with no dependencies
        queue = deque([name for name in plugin_names if in_degree[name] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # Reduce in-degree for plugins that depend on current
            for name in plugin_names:
                if current in dependencies[name]:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(result) != len(plugin_names):
            # Circular dependency detected
            remaining = set(plugin_names) - set(result)
            raise Exception(f"Circular dependency detected among plugins: {remaining}")

        return result

    def run(self, verbose=False):
        """Execute all registered plugins in dependency order."""
        execution_order = self.topological_sort()

        self.db.record_build_time(self.now)

        if verbose:
            print("Plugin execution order:", file=sys.stderr)
            for i, name in enumerate(execution_order, 1):
                print(f"  {i}. {name}", file=sys.stderr)
            print(file=sys.stderr)

        # Ensure all plugins are registered in the database
        for plugin_class in self.plugins:
            self.db.ensure_plugin_registered(plugin_class.name())

        # Execute plugins in order
        for plugin_name in execution_order:
            plugin_class = next(p for p in self.plugins if p.name() == plugin_name)

            if verbose:
                print(f"Running plugin: {plugin_name}", file=sys.stderr)

            plugin = plugin_class(self.db, self.config, now=self.now)
            self.plugin_instances[plugin_name] = plugin

            try:
                plugin.run()
                if verbose:
                    print(f"  ✓ {plugin_name} completed", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ {plugin_name} failed: {e}", file=sys.stderr)
                raise

        if verbose:
            print("\nAll plugins completed successfully", file=sys.stderr)

    def get_plugin(self, name):
        """Get a plugin instance by name (after run() has been called)."""
        return self.plugin_instances.get(name)
