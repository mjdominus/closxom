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
  `default_target_list()`, `dependencies_of(target)`, `build_target(target)`, with generic
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
- Once metadata typing (above) exists, redo path-manipulation code that currently treats
  paths as plain strings to use `pathlib.Path` methods instead. E.g.
  `build_article_pages.py:41` does `relpath.rsplit('.', 1)[0] + '.html'`; once `relpath` is
  a typed `Path`, this should be `relpath.with_suffix('.html')`
- `run-plugin` should discover available plugins at run time instead of importing a
  hardcoded list (`PLUGINS` dict in `run-plugin` currently lists each plugin class by hand)
- `ArticleSkrap.is_published()` does `self.meta['published']`, which raises a raw `KeyError`
  if an article skrap is missing the `published` key (this is intentional — every
  `ArticleSkrap` should have one). At some point add a proper handler for this case (and
  presumably other required-but-missing metadata keys) instead of letting the bare
  `KeyError` propagate
- Need to handle articles that have an explicit publication date in their META section.
  Not yet clear how responsibility for this should be divided between `process_meta`
  (which parses META) and `notyet` (which currently decides published/unpublished status)
- (Low priority — very late, if at all) `genblog` could have a config file giving explicit
  plugin dependency information, as lines of the form `A B -> C D` meaning plugins A and B
  must run before C and D. `genblog` would topologically sort these lines to decide which
  plugins to run and in what order

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
- `process_meta` unconditionally resaves every article on every run (unlike
  `compute_dates`, which correctly checks before saving, and `readfiles`,
  which now does too) — blocks the incremental-rebuild work above, since one
  holdout plugin touching `last_updated` reopens false-staleness cascades for
  everything downstream
