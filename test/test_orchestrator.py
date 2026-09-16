from datetime import datetime, timezone

from closxom.orchestrator import PluginOrchestrator
from closxom.plugin.base import Plugin


class _ProbePlugin(Plugin):
    """A no-op plugin whose only job is to let a test inspect what the
    orchestrator handed it."""

    @classmethod
    def name(cls):
        return "probe"

    @classmethod
    def inputs(cls):
        return []

    @classmethod
    def outputs(cls):
        return []

    def run(self):
        return None


def test_orchestrator_passes_now_to_plugins(skrapdb):
    now = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    orch = PluginOrchestrator(skrapdb, {}, now=now)
    orch.register(_ProbePlugin)
    orch.run()

    assert orch.get_plugin("probe").now == now


def test_orchestrator_defaults_now_to_wall_clock(skrapdb):
    before = datetime.now(timezone.utc)
    orch = PluginOrchestrator(skrapdb, {})
    after = datetime.now(timezone.utc)

    assert before <= orch.now <= after


def test_orchestrator_records_build_time(skrapdb):
    now = datetime(2027, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    orch = PluginOrchestrator(skrapdb, {}, now=now)
    orch.register(_ProbePlugin)
    orch.run()

    assert skrapdb.get_latest_build_time() == now
