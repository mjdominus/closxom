# TODO

## Milestones

- `run-plugin` CLI tool (done): loads a single named plugin by name and calls its `run()`
  method, bypassing the full `genblog` pipeline/orchestrator. `run-plugin plugin-name args...
  --input DIR --db FILE` — trailing args accepted but ignored for now; will be passed to
  `run()` once plugins take arguments.
- Test suite: planned, shape not yet decided.

## Architecture

- Design and document improved plugin API
- New plugin protocol to replace unconditional full-regen `run()`: each plugin implements
  `default_target_list()`, `dependencies_of(target)`, `build(target)`, with generic
  `run(targets=None)` / `need_to_rebuild(target, deps)` on the base `Plugin` class —
  enables incremental rebuilds and partial CLI invocation (e.g. rebuild just one year's archive)
- Layering rule: a plugin's `need_to_rebuild` may only compare against its declared
  dependency skraps (`inputs()`), never reach past them to raw external state
  (e.g. only `scanfiles` may stat the filesystem directly)
- Dependency tracking: considering a `skrap_deps` junction table (`skrap_id`,
  `depends_on_skrap_id`) to record producer → dependency edges explicitly
- Deletion handling: leaning toward tombstoning (mark-deleted flag, not row deletion)
  so dependency FKs never dangle and removal of an input propagates as staleness;
  still open how plugins detect an empty dependency set and how `write_html` removes
  files for tombstoned pages
- Skrap metadata values should carry a type, defaulting to `string` but also supporting
  things like `pathlib.Path` or `int` — similar in spirit to argparse's `type=` parameter
- `run-plugin` should discover available plugins at run time instead of importing a
  hardcoded list (`PLUGINS` dict in `run-plugin` currently lists each plugin class by hand)

## Unimplemented features

- Markdown rendering — `write_html.py` currently just HTML-escapes raw content;
  Markdown syntax is never converted. Decided: use `mistune` (speed, active
  maintenance, closer CommonMark compliance) — not yet wired into the pipeline
- RSS/Atom feed generation
- Templating engine for HTML output (currently hardcoded strings in `write_html.py`)
- Asset handling (images, CSS, JS in the articles directory are ignored)
- Incremental rebuilds (see architecture section above — depends on the new plugin protocol)

## Known bugs

- `cloxsom/article.py` is dead code from the pre-draft era — buggy, unused; delete
  or rewrite as a plugin
- `build_topic_archives` can double-count articles with overlapping tag fields
  (`tags`, `topic`, `category`)
- `readfiles` and `process_meta` unconditionally resave every object on every run
  (unlike `compute_dates`, which correctly checks before saving) — blocks the
  incremental-rebuild work above, since one holdout plugin touching
  `last_modified` reopens false-staleness cascades for everything downstream
