# TODO

Action items for Closxom. Design rationale for the redesign items is in
`notes/redesign-decisions.md`. Small deferred items and still-open questions are
tracked as `lt` threads.

## Redesign: publication + b2c

- [x] `--timezone` CLI flag on `genblog` / `run-plugin` (IANA name), validated
      via `zoneinfo.ZoneInfo` at startup; defaults to `America/New_York` for
      now (interim, see redesign-decisions.md "Timezone semantics")
  - [ ] once configuration can come from a file, drop the default and require
        the value explicitly
  - [ ] `b2c` needs the same required-zone validation
- [x] helper to parse the three `published:` forms (date-only, zoneless
      datetime, offset-bearing) into a UTC instant
- [x] `now` / build-time plumbing
  - [x] `PluginOrchestrator` records one frozen instant at start
  - [x] pass it to plugins via `Plugin.__init__(..., now=None)`, not via `config`
  - [x] `--time` override on `genblog` and `run-plugin`; default is wall-clock
  - [x] record the chosen build time in a DB build-metadata row
- [x] Split publication state into `pubdate` (UTC ISO-8601, or absent) and
      `published` (0/1, recomputed each build)
- [x] Meta ownership / provenance (design: redesign-decisions.md "Meta key
      provenance")
  - [x] `meta.owner_id` column, `NOT NULL`, FK to `plugin(id)`
  - [x] `Plugin.__init__` wraps `db` so `self.db.find_*` binds returned skraps'
        meta to `self.name()`; raw `db` access stays a trusted path
  - [x] replace `save_skrap`'s wholesale meta DELETE+INSERT with owner-scoped
        per-key writes; enforce owner on write, raise on a foreign write
  - [x] `reconcile_meta(skrap, new_dict)` base-class helper
  - [ ] (later) `skrap.meta` as a guarded merged mapping that raises on a
        foreign-key mutation
- [x] Rework `process_meta`
  - [x] `process_meta` now generates each `ArticleSkrap` itself, straight from
        the source `FileSkrap`'s raw content (absorbing `readfiles`, now
        deleted); `content` is always the body only, never the raw
        META-prefixed source, so there's no separate `body` field
  - [x] expose the raw `published:` string; no date parsing here
  - [x] hard-reject a META section with no `title:` (also a missing META
        section entirely - see redesign-decisions.md "Articles with no META
        section")
  - [x] use `reconcile_meta` for its authored keys
  - [x] stop resaving every article every run
- [ ] `fail_article(article, message)` base-class helper
  - [x] trivial version: logs and raises, aborting the run
  - [ ] real behavior: set `published=0`, append to an end-of-run failure
        report; build exits nonzero if any article failed
- [x] Publication-resolver plugin (what `compute_dates` becomes; now
      `resolve_publication`)
  - [x] parse and validate the raw `published:` string via the timezone helper
  - [x] emit `pubdate`; on a malformed value, logged and treated as absent
  - [x] set `published` from `pubdate <= now`
  - [x] runs after `process_meta` automatically (inputs/outputs dependency
        graph; no separate ordering mechanism needed)
  - [x] creates/updates its own `PublicationSkrap` (named after, and
        dependent on, its `ArticleSkrap`) instead of writing `pubdate`/
        `published` onto the article - resolves the meta-provenance
        ownership conflict and lets it use the standard target/dependency
        API (see "Plugin API conversion" below)
  - [ ] (deferred, `lt` vbstr7) a `PublicationSkrap` is only reconsidered
        when its article changes; a future `pubdate` does not by itself
        flip `published` on a later build merely because time passed
- [x] Delete `notyet`: the plugin, `test/plugin/test_notyet.py`, orchestrator/
      `genblog` registration, and `has_notyet` recording in `scanfiles` were
      already gone (`f4fc29e`, before this TODO item was last touched)
- [x] `scanfiles`: tighten the walk to `*.blog`; warn on any stray `.notyet`
- [ ] Write `b2c` (Blosxom -> Closxom converter)
  - [ ] read `/workspace/blosxom-articles`; write a fresh Closxom tree
  - [ ] normalize every article to a META section (`title:` from the first line
        when absent; the second line must be blank, else warn)
  - [ ] `.blog` + empty `.notyet` -> no `published:`; drop the `.notyet`
  - [ ] `.notyet` with content and no `.blog` -> use it as the source, no
        `published:`, no cache lookup
  - [ ] `.blog` with an explicit `published:` -> rewrite as Eastern-local
        ISO-8601 with an offset
  - [ ] `.blog` with no `published:` and no `.notyet` -> cache lookup by path,
        hard-fail on a miss, write Eastern-local ISO-8601 with an offset
  - [ ] strip `published: 0` entirely
  - [ ] warn if an article body already contains a Jinja2 delimiter
        (`{{`, `{%`, `{#`) — it will collide with templating later
  - [ ] ignore everything but `*.blog` / `*.notyet`
  - [ ] fail late: accumulate all offenders, print the list, exit nonzero

## Plugin API conversion

Convert to `default_target_list()` / `dependencies_of()` / `build_target()`.

- [x] `process_meta` (absorbed `readfiles`, which no longer exists)
- [x] `resolve_publication` (via its own `PublicationSkrap`, not by
      annotating the article - see above)
- [ ] `build_article_pages`
- [ ] `build_date_archives`
- [ ] `build_topic_archives`
- [ ] `build_main_page`
- [ ] `write_html`
- `scanfiles` is intentionally exempt (filesystem boundary; overrides `run()`).

## Incremental rebuild

- [ ] `skrap_deps` junction table (`skrap_id`, `depends_on_skrap_id`) recording
      explicit producer -> dependency edges
- [ ] deletion / tombstoning: mark-deleted flag, staleness propagation,
      `write_html` removing files for tombstoned pages (`lt` yhhrg5)
- [ ] explicit plugin-ordering config (`A B -> C D`, topologically sorted)
- [ ] treat the wall-clock dependency of `published` as a staleness input
      (`lt` vbstr7)

## Metadata typing

- [ ] typed meta values (default `string`; also `pathlib.Path`, `int`, ...)
- [ ] then: `build_article_pages.py:41` `relpath.rsplit('.', 1)[0] + '.html'`
      -> `relpath.with_suffix('.html')`

## Features

- [ ] Markdown rendering via `mistune`
- [ ] RSS/Atom feed generation
- [ ] templating engine (replace the hardcoded HTML strings in `write_html.py`)
- [ ] asset handling (images, CSS, JS)

## Bugs / cleanup

- [ ] delete or rewrite dead `closxom/article.py`
- [ ] `build_topic_archives` double-counts articles with overlapping
      `tags` / `topic` / `category`
- [ ] `run-plugin`: discover plugins at runtime instead of the hardcoded
      `PLUGINS` dict
