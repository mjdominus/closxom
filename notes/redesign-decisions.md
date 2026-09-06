# Redesign decisions (in progress)

Running record of decisions from the plugin-API / publication-logic redesign
discussion. Not yet reflected in code except where noted "done".

## Committed so far this cycle

- `a94bef4` — removed obsolete `test_plugin_trivial.py`; fixed skrap type in `test_skrap.py`
- `50e949c` — meta storage changes + `Plugin` meta helpers (see "Meta storage")
- `394fc48` — `notyet` reads `has_notyet` from `FileSkrap.meta` instead of stat'ing the FS

`394fc48` is transitional: the `notyet` plugin is slated for deletion (see
"Publication model"). The meta-storage work stays.

## Meta storage (done)

- `save_skrap_metadata`: JSON-encode compound values only (`dict`/`list`); coerce
  `bool` -> 0/1 (SQLite has no boolean type).
- `_load_metadata`: attempt `json.loads` only on strings starting with `[` or `{`;
  all other scalars pass through verbatim (a scalar string like `"123"` or
  `"null"` is no longer silently reinterpreted).
- `Plugin.update_skrap_meta(skrap, **kwargs)`: assign keys, save once iff a value
  actually changed; bools normalized to 0/1; returns whether a save happened.
- `Plugin.set_skrap_meta_defaults(skrap, **kwargs)`: `dict.setdefault` semantics —
  only fills absent keys, saves iff a key was added.

## scanfiles / readfiles

- `scanfiles` remains the *only* filesystem-boundary plugin.
- `scanfiles` on an mtime change now also **reads the file content** and stores it
  on the `FileSkrap`.
- `scanfiles` directory walk tightened to `*.blog` only (currently `rglob("*")` +
  filters). Drops `has_notyet` recording. Warns if it ever encounters a `.notyet`
  after cutover.
- `readfiles` stays a separate, conventional plugin. Its job: copy
  `FileSkrap.content` -> `ArticleSkrap.content`, establishing the pristine
  known-good starting state.
- `ArticleSkrap.content` stays pristine. Plugins that derive things write
  **separate fields** (e.g. `process_meta` writes meta keys plus a separate
  stripped `body`), never mutate `content` in place — for idempotency and to
  remove inter-plugin ordering fragility.
- TODO: `readfiles` needs more tests (new-article creation, content-unchanged =>
  no resave, missing file).

## Meta key provenance

- A plugin reconciles (adds **and** removes) only the keys it authored. It never
  needs a list of "system" keys — it simply doesn't touch what it didn't write.
- The `$`-prefix "special key" convention was rejected: it can't express
  dual-source keys.
- OPEN: storage mechanism for `process_meta`'s non-interpreted META keys — its own
  skrap replaced wholesale, vs. a tracked key-set. Framing agreed; mechanism not
  finalized.

## Publication model

Split the old `published` field into two:

- `pubdate` — an instant, stored as a UTC ISO-8601 string (see "Timezone
  semantics"), or absent.
- `published` — a boolean, recomputed every build.

| META `published:`                | `pubdate`     | `published` |
|----------------------------------|---------------|-------------|
| absent                           | absent / None | 0           |
| a date/datetime in the future    | that instant  | 0           |
| a date/datetime at or before now | that instant  | 1           |

- Absent `pubdate` means *unconditionally* unpublished. A future `pubdate` is
  stored but `published` stays 0 until the clock passes it.
- The date **cache is eliminated**. `.notyet` files are **eliminated**. The
  `notyet` plugin is **deleted** — along with `test/plugin/test_notyet.py`,
  `test_scanfiles_detects_notyet_marker`, its orchestrator/`genblog`
  registration, and the `has_notyet` meta key.
- All `build_*` plugins already pull `db.find_all_published_articles()`, so
  `published=0` suppresses an article everywhere, including its own page.

## Blosxom -> Closxom converter (`b2c`)

- The converter is named **`b2c`**.
- The input is a copy of the current Blosxom article tree at
  `/workspace/blosxom-articles` — a gitignored subdirectory that is its own
  separate git repository, not part of the Closxom repo.
- The Blosxom tree stays **read-only** until cutover (its code is too unreliable
  to modify in place). `b2c` reads it and writes a fresh Closxom tree, run
  repeatedly during development (diff output against the live blog), with a final
  run at cutover; the old tree is then abandoned and `b2c` retired.
- Single program until it proves too large.
- The Closxom tree is a generated build product, **not hand-edited**, until
  cutover; then the converter is retired and the tree becomes canonical.
- **No Closxom plugin ever writes a `.blog` file.** Date-format rewriting happens
  only in the converter; `process_meta` normalizes internally only.
- Per source file:
  - a `.blog` with an (empty) `.notyet` sibling -> draft: converted article has
    no `published:` line, content from the `.blog`; drop the `.notyet`
  - a `.notyet` with content and **no corresponding `.blog`** -> the `.notyet`
    file *is* the article source (an unpublished draft whose body was never
    promoted to a `.blog`): convert it like any article, no `published:` line, and
    **no cache lookup** (a draft is not expected to be in the cache)
  - a `.blog` with an explicit `published:` -> keep the instant, rewrite it to
    Eastern-local ISO-8601 with an explicit offset (`2006-02-03T12:34:56-05:00`)
  - a `.blog` with no `published:` and no `.notyet` -> look up the date in the
    cache by path (**hard-fail on a cache miss**), render the epoch to
    Eastern-local ISO-8601 with an explicit offset, write that as the
    `published:` value
- Cache file format: `<epoch> <abspath>` lines, all sharing the prefix
  `/home/mjd/misc/blog/entries/`. Strip it, match on the relative path.
- Converter **fails late**: full pass, accumulate every offender (cache miss,
  malformed input, ...), print the list, exit nonzero.
- Converter strips `published: 0` entirely — absent is the canonical form for
  "unpublished".
- Only `*.blog` and `*.notyet` files are relevant. Everything else in the tree is
  ignored completely (Blosxom template-expansion files will live elsewhere in
  Closxom).
- Articles are never renamed (URL stability). A future plugin will handle renames
  by writing a redirect page at the old path.

### Articles with no META section

- The converter **normalizes every article to have a META section**. The no-META
  form does not survive into the Closxom tree.
- For a source article with no META section: the **title is the first line**, the
  **second line must be blank** (warn if it isn't), and the body is the remaining
  lines. The converter synthesizes:

  ```
  META
  title: <first line>
  published: <cache epoch, as Eastern-local ISO-8601 with offset>

  <body: line 3 onward>
  ```

- `process_meta`'s no-META branch (first line as title) is therefore **obsolete
  and is removed** — it predates the decision to convert all article files.

## process_meta (going forward)

- Accepts exactly these forms for `published:` (no unix timestamps, no `/`
  separators):
  - `YYYY-MM-DD` — interpreted as **noon in the config zone**
  - zoneless `YYYY-MM-DDThh:mm:ss` — that wall time in the config zone
  - offset-bearing `YYYY-MM-DDThh:mm:ss±hh:mm` (or `...Z`) — taken as-is
  - absent
- All forms normalize to one instant, stored as `pubdate` in UTC ISO-8601
  (see "Timezone semantics"). Parses and validates the field; emits `pubdate`
  or nothing.
- A META section with **no `title:` is a hard rejection** — titles are required,
  matching the current software.
- The no-META branch (first line as title) is **removed** — post-conversion every
  article has a META section.
- On a malformed `published:` value, `process_meta` raises. The exception is
  caught in the plugin's **own per-article loop** (not the orchestrator, which
  does not iterate articles). The article gets `published=0`, a diagnostic, and an
  entry in an end-of-run failure report.
- Standardize this via a base-class helper, e.g. `self.fail_article(article,
  message)`.
- A build that skipped one or more broken articles exits nonzero with a summary.

## compute_dates (going forward)

- Near-total rewrite. Drops the mtime fallback, unix-timestamp parsing, the
  `%Y/%m/%d` format, and the `date` key.
- New job: read `pubdate`, compare it to `now` (both UTC), set `published`. The
  only step that touches the clock. Comparison is on parsed datetimes, not raw
  strings.
- OPEN: keep the name, or rename to `resolve-publication`.

## `now` plumbing

- A single frozen instant, recorded by `PluginOrchestrator` at start — not a
  callable (determinism).
- Passed to plugins via `Plugin.__init__(self, db, config=None, now=None)` or an
  orchestrator-set attribute — **not** through `config`.
- `genblog` and `run-plugin` get a `--time` override; default is wall-clock. A
  zoneless `--time` is interpreted in the config zone (a date-only `--time` is
  noon in the config zone); stored/compared as UTC.
- Recorded in a DB build-metadata row. Name it `build_time` / `as_of`.

## Timezone semantics

- The config zone (an IANA name, e.g. `America/New_York`) is a **required** key in
  `config`. No default — `genblog` and the converter both fail loudly if it is
  missing. Validated at startup by constructing `zoneinfo.ZoneInfo(name)`.
- One blog-wide zone; no per-article override.
- Zoneless values in `published:` are interpreted in the config zone. A
  date-only value is **noon** in that zone (not midnight — noon is never near a
  DST transition and has ~12h of slack before any conversion crosses a calendar
  day).
- `published:` may carry an explicit offset; it is honored as an instant. The
  post still has a single publication date driving everything, rendered in the
  config zone for output (an article given a Seoul-morning `published:` can show
  a previous-evening Eastern date on the generated pages — acceptable).
- **Stored dates are UTC**, ISO-8601, in the form `datetime.isoformat()` emits
  (`2027-05-31T20:00:00+00:00`). Applies to `pubdate` and `build_time`.
- The **converter** writes `published:` into the `.blog` files as Eastern-local
  ISO-8601 **with an explicit offset** — readable as local time, but the instant
  is pinned exactly and independently of the config value.
- Consumers that order by date (e.g. `build_main_page`, which currently builds
  `(meta['date'], id)` tuples and sorts them — fine while `date` is a float)
  must parse the ISO string to a `datetime` before comparing/sorting.

## Deferred

- The wall-clock dependency of `published` (a future-dated post flips with no file
  change) as an input to incremental-rebuild staleness — noted, not blocking.
