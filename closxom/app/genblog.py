"""Generate a static blog from article files using the closxom plugin system.

The `genblog` script at the repo root is a thin wrapper around run() here.
"""

import argparse
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from closxom.db import DB
from closxom.orchestrator import PluginOrchestrator
from closxom.pubdate import InvalidInstantValue, resolve_time

# Import all plugins
from closxom.plugin.scanfiles import ScanFilesPlugin
from closxom.plugin.process_meta import ProcessMetaPlugin
from closxom.plugin.resolve_publication import ResolvePublicationPlugin
from closxom.plugin.formatter import FormatterPlugin
from closxom.plugin.plan_article_page import PlanArticlePagePlugin
from closxom.plugin.write_html import WriteHtmlPlugin


def run(argv=None):
    parser = argparse.ArgumentParser(description="Generate static blog")
    parser.add_argument('--db', default='closxom.db',
                        help='Database file (default: closxom.db)')
    parser.add_argument('--input', default='articles',
                        help='Input directory (default: articles)')
    parser.add_argument('--output', default='output',
                        help='Output directory (default: output)')
    parser.add_argument('--schema', default='SCHEMA',
                        help='Schema directory (default: SCHEMA)')
    parser.add_argument('--create-db', action='store_true',
                        help='Create fresh database (destroys existing)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--recent', type=int, default=12,
                        help='Number of recent articles on main page (default: 12)')
    # Defaults to America/New_York only because configuration is CLI-flags-only
    # for now. Once file-based config exists this default goes away and the
    # value becomes required - see notes/redesign-decisions.md.
    parser.add_argument('--timezone', default='America/New_York',
                        help='IANA timezone for interpreting dates (default: America/New_York)')
    parser.add_argument('--time', default=None,
                        help='Build time override (default: current time); '
                             'parsed like a published: value, in --timezone')

    args = parser.parse_args(argv)

    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        print(f"Error: unknown timezone {args.timezone!r}", file=sys.stderr)
        return 1

    try:
        now = resolve_time(args.time, args.timezone)
    except InvalidInstantValue as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create or open database
    db_path = Path(args.db)
    if args.create_db or not db_path.exists():
        if db_path.exists():
            db_path.unlink()
            if args.verbose:
                print(f"Removed existing database: {db_path}", file=sys.stderr)

        db = DB(args.db)
        db.create_tables(Path(args.schema))
        if args.verbose:
            print(f"Created database: {db_path}", file=sys.stderr)
    else:
        db = DB(args.db)
        if args.verbose:
            print(f"Using existing database: {db_path}", file=sys.stderr)

    # Create orchestrator and register plugins
    config = {
        'input_dir': args.input,
        'output_dir': args.output,
        'recent': args.recent,
        'timezone': args.timezone,
    }
    orchestrator = PluginOrchestrator(db, config, now=now)

    # File handling plugins
    orchestrator.register(ScanFilesPlugin)

    # Article processing plugins
    orchestrator.register(ProcessMetaPlugin)
    orchestrator.register(ResolvePublicationPlugin)
    orchestrator.register(FormatterPlugin)

    # Page planning plugins
    orchestrator.register(PlanArticlePagePlugin)

    # Output plugins
    orchestrator.register(WriteHtmlPlugin)

    # Run the orchestrator
    try:
        if args.verbose:
            print("\n=== Starting blog generation ===\n", file=sys.stderr)

        orchestrator.run(verbose=args.verbose)

        if args.verbose:
            print(f"\n=== Blog generation complete ===", file=sys.stderr)
            print(f"Output written to: {args.output}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
