# Redesign decisions

Settled design decisions for the plugin-API and publication-logic redesign, with
rationale. This file is a reference, not a task list — action items are in
`../TODO.md`. Still-open questions are listed at the end and tracked as `lt`
threads.

## Implemented so far

- `a94bef4` — removed obsolete `test_plugin_trivial.py`; fixed skrap type in `test_skrap.py`
- `50e949c` — meta storage changes + `Plugin` meta helpers
- `394fc48` — `notyet` reads `has_notyet` from `FileSkrap.meta` (transitional; `notyet` is to be deleted)
- `4f3cc25` — `scanfiles` loads file content onto the `FileSkrap`; `readfiles` rewritten as a pure copy
- `2ba6393` — return annotations on the abstract `Plugin` methods to quiet basedpyright

## Meta storage

- `save_skrap_metadata` JSON-encodes compound values only (`dict` / `list`) and
  coerces `bool` to 0/1, since SQLite has no boolean type.
- `_load_metadata` attempts `json.loads` only on strings starting with `[` or
  `{`; every other scalar passes through verbatim, so a scalar string like
  `"123"` or `"null"` is not silently reinterpreted.
- `Plugin.update_skrap_meta(skrap, **kwargs)` assigns keys and saves once, only
  if a value actually changed; bools are normalized to 0/1; it returns whether a
  save happened.
- `Plugin.set_skrap_meta_defaults(skrap, **kwargs)` has `dict.setdefault`
  semantics — fills only absent keys, saves only if a key was added.

## Article content: scanfiles, readfiles, pristine content

- `scanfiles` is the only filesystem-boundary plugin. It reads file content on a
  new or changed file and stores it on the `FileSkrap`. Its walk is `*.blog`
  only.
- `readfiles` is a conventional plugin that copies `FileSkrap.content` ->
  `ArticleSkrap.content`, establishing a pristine known-good starting state. It
  does not touch the filesystem.
- `ArticleSkrap.content` stays pristine for the life of the pipeline. A plugin
  that derives something from it writes a **separate field** (e.g. `process_meta`
  writes a `body` field with the META block removed) rather than mutating
  `content` in place. This keeps every plugin's input stable, makes re-runs
  idempotent, and removes inter-plugin ordering fragility.

## Meta key provenance

- A plugin reconciles — adds *and* removes — only the meta keys it authored. It
  never needs a list of "system" keys; it simply does not touch what it did not
  write. So a key an author deletes from a file's META section on a later edit
  also disappears from `article.meta`, while `path` / `relpath` / etc. are left
  alone.
- The `$`-prefix "special key" convention was rejected: a single special/ordinary
  bit cannot express a key that legitimately has more than one possible source.

### Mechanism

- The `meta` table gets an `owner_id` column, `NOT NULL`, FK to `plugin(id)` —
  the same shape as `skrap.owner_id`. Every `meta` row records the one plugin
  that writes it.
- **Invariant: every meta key has exactly one writer.** Two plugins never share a
  key. If A and B each want a `perfume`-like value they use distinct names
  (`a_perfume`, `b_perfume`). The raw `published:` header string (owned by
  `process_meta`) and the resolver's derived value are therefore different keys.
- A plugin may write a `meta` key for a skrap when the key does not yet exist —
  it then becomes the owner — or when it already is the owner. Updating or
  deleting a key owned by another plugin raises and fails the plugin.
  Enforcement lives at persist time in the DB layer and is authoritative; the
  in-memory guard below is a fast-feedback aid and may land later.
- The writer identity is injected once: `Plugin.__init__` wraps the `db` handle
  so `self.db.find_*` returns skraps whose `meta` is bound to `self.name()`.
  Existing `self.db.find_*` call sites are unchanged. Raw `db` access with no
  writer identity (tests, glue code) is a trusted path and skips the check.
- `skrap.meta` stays a **single merged mapping** over all rows regardless of
  owner — readers keep one place to look. It is a custom mapping that knows the
  per-key owner and the current writer; mutating a foreign key (`__setitem__`,
  `__delitem__`, `pop`, `update`, `setdefault`, `clear`) raises. Foreign values
  are handed out as copies / immutable so in-place mutation cannot quietly
  bypass the guard.
- Reconciliation stays explicit but is a base-class helper —
  `reconcile_meta(skrap, new_dict)` keyed on `self.name()`: write `new_dict`,
  then delete this plugin's own rows for the skrap that are absent from it. The
  prior key-set comes from the table (`WHERE skrap_id=? AND owner_id=?`), so
  there is no separate bookkeeping record.
- Consequence: `save_skrap`'s current wholesale meta DELETE + re-INSERT is
  replaced by owner-scoped per-key writes. `skrap.meta` becomes read-oriented;
  writes go through `update_skrap_meta` / `set_skrap_meta_defaults` /
  `set_meta` / `reconcile_meta`, all carrying `self.name()`.

## Publication model

Publication state is two fields:

- `pubdate` — an instant, stored as a UTC ISO-8601 string, or absent.
- `published` — 0 or 1, recomputed every build.

| `published:` in META                | `pubdate`     | `published` |
|-------------------------------------|---------------|-------------|
| absent                              | absent / None | 0           |
| a date/datetime in the future       | that instant  | 0           |
| a date/datetime at or before `now`  | that instant  | 1           |

- Absent `pubdate` is *unconditionally* unpublished. A future `pubdate` is stored
  but `published` stays 0 until the build clock passes it.
- The old article-date **cache is eliminated**. `.notyet` files are
  **eliminated** (`b2c` converts them). The `notyet` plugin is **deleted**.
- Every `build_*` plugin already pulls `db.find_all_published_articles()`, so
  `published = 0` suppresses an article everywhere, including its own page.

Rationale: the historical logic conflated a boolean with a date and split
responsibility for it across `process_meta`, `notyet`, and a sticky mtime cache.
Two fields and one decision table replace all of that.

## Blosxom -> Closxom conversion (`b2c`)

- The converter is named `b2c`. Its input is a copy of the current Blosxom
  article tree at `/workspace/blosxom-articles` — a gitignored subdirectory that
  is its own separate git repository, not part of the Closxom repo.
- The Blosxom tree stays read-only until cutover; its own code is too unreliable
  to modify in place. `b2c` reads it and writes a fresh Closxom tree, run
  repeatedly during development (diffing output against the live blog), with a
  final run at cutover. Afterwards the old tree is abandoned and `b2c` retired.
- Until cutover the Closxom tree is a generated build product, never hand-edited.
  At cutover it becomes canonical.
- No Closxom plugin ever writes a `.blog` file. Date-format rewriting happens
  only in `b2c`.
- Per source file:
  - a `.blog` with an empty `.notyet` sibling -> draft: no `published:` line,
    content from the `.blog`; the `.notyet` is dropped
  - a `.notyet` with content and no corresponding `.blog` -> the `.notyet` file
    is the article source (a draft whose body was never promoted to a `.blog`):
    convert it like any article, no `published:` line, no cache lookup
  - a `.blog` with an explicit `published:` -> keep the instant, rewrite it as
    Eastern-local ISO-8601 with an explicit offset (`2006-02-03T12:34:56-05:00`)
  - a `.blog` with no `published:` and no `.notyet` -> look up the date in the
    cache by path (hard-fail on a miss), render the epoch as Eastern-local
    ISO-8601 with an explicit offset
- Cache file format: `<epoch> <abspath>` lines, all sharing the prefix
  `/home/mjd/misc/blog/entries/`; strip it and match on the relative path.
- `b2c` fails late: one full pass, accumulate every offender (cache miss,
  malformed input), print the list, exit nonzero.
- `published: 0` is stripped entirely; absent is the canonical "unpublished"
  form.
- Only `*.blog` and `*.notyet` files matter; everything else is ignored (Blosxom
  template-expansion files live elsewhere in Closxom).
- Articles are never renamed (URL stability). A future plugin will handle renames
  by writing a redirect page at the old path.

### Articles with no META section

- `b2c` normalizes every article to have a META section; the no-META form does
  not survive into the Closxom tree.
- For a source file with no META section, the title is the first line, the second
  line must be blank (warn otherwise), and the body is the rest:

  ```
  META
  title: <first line>
  published: <cache epoch, as Eastern-local ISO-8601 with offset>

  <body: line 3 onward>
  ```

## `process_meta`

- `process_meta` is a mechanical META-block handler. It splits the META headers
  from the body, writes the body to a separate `body` field (leaving `content`
  pristine), and populates `article.meta` from the headers.
- It does **not** parse or validate `published:` — it exposes the raw string and
  the publication resolver does everything date-related. This keeps `zoneinfo`
  and date-format concerns out of `process_meta`.
- A META section with no `title:` is a hard rejection; titles are required,
  matching the current software. (There is no longer a no-META branch — every
  article has a META section after `b2c`.)
- It reconciles only the meta keys it authored (see Meta key provenance).

## Publication resolver (formerly `compute_dates`)

- `compute_dates` is rewritten into the one plugin that owns all publication
  logic. The mtime fallback, unix-timestamp parsing, the `%Y/%m/%d` format, and
  the `date` key are all dropped.
- It parses and validates the raw `published:` string via the timezone helper,
  emits `pubdate` (UTC ISO-8601) or nothing, and sets `published` from
  `pubdate <= now`. Comparison is on parsed datetimes, not raw strings.
- On a malformed `published:` value it raises; the exception is caught in the
  plugin's own per-article loop (the orchestrator does not iterate articles). The
  article gets `published = 0`, a diagnostic, and an entry in an end-of-run
  failure report; a build that skipped any article exits nonzero.
- It must run after `process_meta`. Both have `inputs = ["article"]`,
  `outputs = []`, so the orchestrator's inputs/outputs topological sort will not
  order them — an explicit ordering mechanism is needed.

## `now` / build time

- `PluginOrchestrator` records one frozen instant at start — a value, not a
  callable, so a build is deterministic and reproducible.
- It reaches plugins through `Plugin.__init__(self, db, config=None, now=None)`
  or an orchestrator-set attribute, not through `config` (which holds
  entry-point settings, not orchestrator-generated state).
- `genblog` and `run-plugin` take a `--time` override; the default is
  wall-clock. A zoneless `--time` is interpreted in the config zone (a date-only
  `--time` is noon there); it is stored and compared as UTC.
- The chosen build time is recorded in a DB build-metadata row. Working name:
  `build_time` / `as_of`.

## Timezone semantics

- The config zone (an IANA name, e.g. `America/New_York`) lives in `config`. One
  blog-wide zone; no per-article override. `genblog`/`run-plugin` fail at
  startup if the value is not constructible as `zoneinfo.ZoneInfo`.
- **Interim, while configuration is CLI-flags-only:** `--timezone` defaults to
  `America/New_York`, since there is nowhere yet to put a required value that
  isn't typed on every invocation. Once file-based configuration exists, the
  default must be removed and the value made required with no fallback — a
  CLI default is a silent-wrong-zone hazard exactly like the one the required
  config key was meant to prevent, and it should not persist longer than the
  CLI-only phase demands.
- `published:` accepts exactly: `YYYY-MM-DD` (noon in the config zone), a
  zoneless `YYYY-MM-DDThh:mm:ss` (that wall time in the config zone), or an
  offset-bearing datetime / `...Z` (taken as the instant it names). No unix
  timestamps, no `/` separators.
- Date-only values are noon, not midnight: noon is never near a DST transition
  and has ~12 h of slack before any zone conversion could cross a calendar day,
  so `YYYY-MM-DD` always names a real, unambiguous instant that stays in the
  right archive month.
- An explicit offset is honored as an instant. The post still has one publication
  date driving everything, rendered in the config zone for output — an article
  given a Seoul-morning `published:` may show a previous-evening Eastern date on
  the generated pages, which is acceptable.
- Stored dates are UTC ISO-8601 in the form `datetime.isoformat()` emits
  (`2027-05-31T20:00:00+00:00`). Applies to `pubdate` and `build_time`.
- `b2c` writes `published:` into the `.blog` files as Eastern-local ISO-8601
  **with an explicit offset** — readable as local time, but the instant is pinned
  exactly and independently of the config value.
- Consumers that order by date (e.g. `build_main_page`) must parse the ISO string
  to a `datetime` before comparing or sorting.

## Open questions

- **Publication-resolver plugin name** — keep `compute_dates` or rename to
  `resolve-publication`. (`lt` jwnuu5)
- **`published` recompute vs. incremental-rebuild staleness** — a future-dated
  post flips with no file change; `build_time` must be a staleness input for
  anything gated on `published`. (`lt` vbstr7)
- **Article-file deletion handling** — tombstoning direction agreed; detection of
  an emptied dependency set and output-file removal still undecided.
  (`lt` yhhrg5)
