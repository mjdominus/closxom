"""Every plugin the orchestrator can register must accept (db, config, now)
uniformly, since PluginOrchestrator.run() instantiates all of them the same
way. A plugin with its own __init__ that doesn't forward one of these three
breaks silently only when actually orchestrated - so pin it here instead."""

from datetime import datetime, timezone

from closxom.plugin.resolve_publication import ResolvePublicationPlugin
from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.plugin.formatter import FormatterPlugin
from closxom.plugin.plan_article_page import PlanArticlePagePlugin
from closxom.plugin.scanfiles import ScanFilesPlugin
from closxom.plugin.write_html import WriteHtmlPlugin

ALL_PLUGINS = [
    ScanFilesPlugin,
    ProcessMetaPlugin,
    ResolvePublicationPlugin,
    FormatterPlugin,
    PlanArticlePagePlugin,
    WriteHtmlPlugin,
]


def test_every_plugin_accepts_db_config_and_now(skrapdb):
    now = datetime(2027, 6, 1, tzinfo=timezone.utc)
    for plugin_class in ALL_PLUGINS:
        plugin = plugin_class(skrapdb, {}, now=now)
        assert plugin.now == now, plugin_class
