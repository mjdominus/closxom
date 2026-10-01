"""Run a single closxom plugin in isolation, outside the full genblog pipeline.

The `run-plugin` script at the repo root is a thin wrapper around run() here.
"""

import argparse
import logging
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from closxom.db import DB
from closxom import logconfig
from closxom.pubdate import InvalidInstantValue, resolve_time

from closxom.plugin.scanfiles import ScanFilesPlugin
from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.plugin.resolve_publication import ResolvePublicationPlugin
from closxom.plugin.write_html import WriteHtmlPlugin

PLUGINS = {
    cls.name(): cls
    for cls in [
        ScanFilesPlugin,
        ProcessMetaPlugin,
        ResolvePublicationPlugin,
        WriteHtmlPlugin,
    ]
}


def run(argv=None):
    parser = argparse.ArgumentParser(description="Run a single closxom plugin in isolation")
    parser.add_argument('plugin', choices=sorted(PLUGINS), help='Plugin to run')
    parser.add_argument('args', nargs='*',
                        help='Arguments for the plugin (currently ignored)')
    parser.add_argument('--db', default='closxom.db',
                        help='Database file (default: closxom.db)')
    parser.add_argument('--input', default='articles',
                        help='Input directory (default: articles)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose logging')
    # Defaults to America/New_York only because configuration is CLI-flags-only
    # for now. Once file-based config exists this default goes away and the
    # value becomes required - see notes/redesign-decisions.md.
    parser.add_argument('--timezone', default='America/New_York',
                        help='IANA timezone for interpreting dates (default: America/New_York)')
    parser.add_argument('--time', default=None,
                        help='Build time override (default: current time); '
                             'parsed like a published: value, in --timezone')

    parsed = parser.parse_args(argv)

    try:
        ZoneInfo(parsed.timezone)
    except ZoneInfoNotFoundError:
        print(f"Error: unknown timezone {parsed.timezone!r}", file=sys.stderr)
        return 1

    try:
        now = resolve_time(parsed.time, parsed.timezone)
    except InvalidInstantValue as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    logconfig.configure(level=logging.DEBUG if parsed.verbose else logging.WARNING)

    db = DB(parsed.db)
    config = {'input_dir': parsed.input, 'timezone': parsed.timezone}
    db.record_build_time(now)

    plugin_class = PLUGINS[parsed.plugin]
    plugin = plugin_class(db, config, now=now)
    result = plugin.run()
    print(result, file=sys.stderr)

    return 0
