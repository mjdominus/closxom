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
- `build_article_pages` / `build_date_archives` / `build_topic_archives` /
  `build_main_page` deleted 2026-10-01 - see "Page building plugins" below
- `scanfiles` is intentionally exempt (filesystem boundary; overrides `run()`).
- `write_html` is also intentionally exempt, like `scanfiles` - a filesystem
  boundary in the opposite direction (writing out, not reading in), comparing
  a plan's `last_updated` against the output file's own mtime instead of the
  generic skrap-to-skrap dependency check

## Page building plugins

`build_article_pages`, `build_date_archives`, `build_topic_archives`, and
`build_main_page` were deleted 2026-10-01: pre-date the `.content`/provenance/
target-dependency design (every one always constructed a fresh `PageSkrap`
instead of find-or-create, so each crashed on `UNIQUE constraint failed` the
first time it was rerun against any published article - confirmed by actually
running `genblog` twice), had zero test coverage, and three of the four sorted
by an `article.meta['date']` key nothing has ever written. Not worth patching;
redo from scratch.

- [x] decided 2026-10-01/02: a separate family of planner plugins first
      produces a `PlanSkrap` ("fill template X with values {...} and the
      contents of skraps s1, s2, ..."), named for the *output* file it
      pertains to (not any input file - a plan doesn't map one-to-one with
      input files; archive/feed plans aggregate many), for `write_html` (and
      eventually `write_rss`/`write_atom`) to execute. `plan-article-page`
      (single-article page) implemented 2026-10-02 as the first instance -
      see `closxom/plugin/plan_article_page.py`
  - [x] `write_html` rewritten 2026-10-02 to consume `plan` instead of the
        old `page` shape: reads `built_from`-referenced skraps' content
        (not `ArticleSkrap.content`), no longer double-escapes already-
        rendered HTML, compares `plan.last_updated` against the output
        file's own mtime for staleness (overriding `run()`, same shape as
        `scanfiles`, not the generic target/dependency API - no tracking
        skrap needed). Verified end-to-end against `sample/`.
  - [ ] the planner family for aggregating pages (date/topic archives, main
        page) is still unbuilt; when it is, every `PlanSkrap` it produces
        must stay format-agnostic ("here's the math-tagged article set and
        its relevant data"), not shaped around what an HTML template
        happens to need - confirmed 2026-10-02 that `write_rss`/`write_atom`
        (see "Features" below) will consume the *same* Plan skraps as
        `write_html` for these aggregating pages, not a separate planner;
        `plan-article-page` is exempt from this, there being no per-article
        feed entry file
  - [ ] watch for the double-counting bug the deleted `build_topic_archives`
        had: an article with overlapping `tags` / `topic` / `category`
        values got counted into the same topic more than once
  - [ ] aggregating pages needed, confirmed 2026-10-04: year, month, and
        "source directory" (Blosxom-style directory-as-category, not a META
        `tags:`/`topic:` key - different grouping than the deleted
        `build_topic_archives` used). Year and month are the easier pair:
        every published article has exactly one unambiguous year/month from
        its already-validated `pubdate`; directory grouping raises real
        open questions first (does a nested `dir/subdir/article.blog`
        belong to both archives or just the immediate parent? what about an
        article with no subdirectory at all?)
  - [ ] the old blog also has single-*day* aggregate pages (almost always
        one article, but not always) at URLs like `/2026/04/02.html` - these
        must keep resolving; fold into the year/month archive work rather
        than treating it as a fourth, separate thing
  - [ ] found 2026-10-04, confirmed by actually editing an article's body
        and rerunning: `plan_article_page` + `write_html` have a real
        staleness bug. A `PlanSkrap`'s `values`/`built_from` only ever
        stored a *reference* to the `HTMLSkrap`, never its content, so an
        article's title/pubdate not changing means the Plan's own meta is
        byte-identical even when the body did change - `reconcile_meta`
        sees nothing to save, `plan.last_updated` never advances, and
        `write_html`'s mtime check wrongly treats the stale output file as
        current. Fix (also unifies single- and multi-article templates,
        confirmed 2026-10-04): `values` becomes `{'articles': [{'title',
        'date', 'content', 'url', ...}, ...]}` - one element for a
        single-article page, many for an archive - with each `content`
        already resolved and ready to drop into the template (Jinja2
        `| safe`) rather than dereferenced later by `write_html`.
        `built_from` stays a separate list of skrap refs, purely for the
        deletion-detection purpose (`lt` yhhrg5) - no longer doing double
        duty as what gets rendered. Needs applying to the already-built
        `plan_article_page.py`/`write_html.render_single_article`, not just
        the new aggregating planners.

## Incremental rebuild

- rejected 2026-10-01 (`lt` yhhrg5): a `skrap_deps` junction table
  (`skrap_id`, `depends_on_skrap_id`) for reverse-lookup ("X disappeared, who
  depended on it"). Unnecessary: a multi-input planner's `default_target_list()`
  includes every existing output of its own type, not just ones derivable
  from current inputs, so an orphaned output stays visited forever and
  self-detects via its own `built_from` field - no reverse index needed
- [ ] deletion / tombstoning: mark-deleted flag, staleness propagation,
      `write_html` removing files for tombstoned pages (`lt` yhhrg5)
- [ ] explicit plugin-ordering config (`A B -> C D`, topologically sorted)
- [ ] treat the wall-clock dependency of `published` as a staleness input
      (`lt` vbstr7)

## Metadata typing

See `notes/redesign-decisions.md`, "Metadata typing", for why.

- [ ] typed meta values (default `string`; also `pathlib.Path`, `int`, ...)

## Content mutator plugins

Plugins that rewrite `ArticleSkrap.content` in place (macro expansion, `WPREF/foo`
-> Wikipedia URLs, `<book>...</book>` expansion from a book database, probably
others). See `notes/redesign-decisions.md`, "Meta key provenance" UPDATE
2026-09-30, for the design.

- [x] DB permits a skrap's own row owner to clear (not mutate) a meta key
      owned by a different plugin
- [ ] each mutator marks its own progress with a meta key it owns, called a
      "footprint": a flag, or a content hash, to also skip re-running
      expensive ones cheaply
- [ ] `process_meta` clears every mutator's footprint when it regenerates an
      article's content from scratch (via the row-owner-clear permission above)
- [ ] first mutator plugin: macro expansion
- [ ] `WPREF/foo` -> `https://en.wikipedia.org/wiki/foo` link rewriting
- [ ] `<book>...</book>` expansion from a book database
- [ ] ordering between mutators, if it ever turns out to matter for a specific
      pair (most are expected to commute); deferred, no mechanism needed yet

## Features

- [x] Markdown rendering via `mistune` - the "formatter" plugin
  - [x] handle `formatter: markdown` (render via `mistune`), explicit or
        absent (the default), and `formatter: raw` (pass through unchanged,
        for source files `b2c` recognizes as already being HTML); any other
        value fails the article
  - [x] result is a new skrap of a new type (tentatively `HTMLSkrap`),
        depending on the `ArticleSkrap`, not a mutation of it - same reasoning
        as `PublicationSkrap`
- [ ] RSS/Atom feed generation
- [ ] templating engine via Jinja2 (replace the hardcoded HTML strings in
      `write_html.py`; see `lt` 2026-10-03-8wjbxa)
- [ ] asset handling (images, CSS, JS)

## Bugs / cleanup

- [ ] delete or rewrite dead `closxom/article.py`
- [ ] `run-plugin`: discover plugins at runtime instead of the hardcoded
      `PLUGINS` dict
