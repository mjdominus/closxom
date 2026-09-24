"""Every plugin the orchestrator can register must accept (db, config, now)
uniformly, since PluginOrchestrator.run() instantiates all of them the same
way. A plugin with its own __init__ that doesn't forward one of these three
breaks silently only when actually orchestrated - so pin it here instead."""

from datetime import datetime, timezone

from closxom.plugin.build_article_pages import BuildArticlePagesPlugin
from closxom.plugin.build_date_archives import BuildDateArchivesPlugin
from closxom.plugin.build_main_page import BuildMainPagePlugin
from closxom.plugin.build_topic_archives import BuildTopicArchivesPlugin
from closxom.plugin.resolve_publication import ResolvePublicationPlugin
from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.plugin.readfiles import ReadFilesPlugin
from closxom.plugin.scanfiles import ScanFilesPlugin
from closxom.plugin.write_html import WriteHtmlPlugin

ALL_PLUGINS = [
    ScanFilesPlugin,
    ReadFilesPlugin,
    ProcessMetaPlugin,
    ResolvePublicationPlugin,
    BuildArticlePagesPlugin,
    BuildDateArchivesPlugin,
    BuildTopicArchivesPlugin,
    BuildMainPagePlugin,
    WriteHtmlPlugin,
]


def test_every_plugin_accepts_db_config_and_now(skrapdb):
    now = datetime(2027, 6, 1, tzinfo=timezone.utc)
    for plugin_class in ALL_PLUGINS:
        plugin = plugin_class(skrapdb, {}, now=now)
        assert plugin.now == now, plugin_class
