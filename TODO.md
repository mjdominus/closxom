# TODO

Action items for Closxom. Design rationale for the redesign items is in
`notes/redesign-decisions.md`. Small deferred items and still-open questions are
tracked as `lt` threads.

## Redesign: publication + b2c

- [ ] Timezone plumbing
  - [ ] required `timezone` key in `config` (IANA name); `genblog` and `b2c`
        fail at startup if it is missing or not constructible as
        `zoneinfo.ZoneInfo`
  - [ ] helper to parse the three `published:` forms (date-only, zoneless
        datetime, offset-bearing) into a UTC instant
- [ ] `now` / build-time plumbing
  - [ ] `PluginOrchestrator` records one frozen instant at start
  - [ ] pass it to plugins via `Plugin.__init__(..., now=None)`, not via `config`
  - [ ] `--time` override on `genblog` and `run-plugin`; default is wall-clock
  - [ ] record the chosen build time in a DB build-metadata row
- [ ] Split publication state into `pubdate` (UTC ISO-8601, or absent) and
      `published` (0/1, recomputed each build)
- [ ] Rework `process_meta`
  - [ ] split the META block from the body; write the body to a separate `body`
        field and leave `content` pristine
  - [ ] expose the raw `published:` string; no date parsing here
  - [ ] hard-reject a META section with no `title:`
  - [ ] reconcile only the meta keys it authored (mechanism: `lt` y28ws8)
  - [ ] stop resaving every article every run
- [ ] `fail_article(article, message)` base-class helper: log, set
      `published=0`, append to an end-of-run failure report; build exits nonzero
      if any article failed
- [ ] Publication-resolver plugin (what `compute_dates` becomes)
  - [ ] parse and validate the raw `published:` string via the timezone helper
  - [ ] emit `pubdate`; on a malformed value raise, caught per-article
  - [ ] set `published` from `pubdate <= now`
  - [ ] must run after `process_meta` (needs an explicit ordering mechanism)
- [ ] Delete `notyet` (same commit as the resolver): the plugin,
      `test/plugin/test_notyet.py`, `test_scanfiles_detects_notyet_marker`,
      orchestrator/`genblog` registration, `has_notyet` recording in `scanfiles`
- [ ] `scanfiles`: tighten the walk to `*.blog`; warn on any stray `.notyet`
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
  - [ ] ignore everything but `*.blog` / `*.notyet`
  - [ ] fail late: accumulate all offenders, print the list, exit nonzero

## Plugin API conversion

Convert to `default_target_list()` / `dependencies_of()` / `build_target()`.

- [x] `readfiles`
- [ ] `process_meta`
- [ ] `compute_dates` / publication-resolver
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

- [ ] delete or rewrite dead `cloxsom/article.py`
- [ ] `build_topic_archives` double-counts articles with overlapping
      `tags` / `topic` / `category`
- [ ] `run-plugin`: discover plugins at runtime instead of the hardcoded
      `PLUGINS` dict
- [ ] rename the package `cloxsom` -> `closxom` (`lt` 46cvdv; also `CLAUDE.md`)
