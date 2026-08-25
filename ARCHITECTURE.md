# Closxom Architecture

Closxom (née suxsom) is a custom static blog generator written in Python, designed
to replace a long-running Blosxom installation.  The codebase is currently in the
`claude` branch; `master` has only the schema and early stubs.

The package is named `cloxsom` throughout the code, matching the project name.

## Core idea

Everything produced during a blog-generation run is a **skrap** — a typed product
object stored in SQLite.  Plugins read and write skrap objects.  The orchestrator
runs plugins in dependency order.  A single entry-point script (`genblog`) drives
the whole thing.

## Pipeline (current plugin order)

```
filesystem
    → [scanfiles]   → FileSkrap (one per input file)
    → [readfiles]   → ArticleSkrap (raw content)
    → [notyet]      → marks unpublished articles (modifies in place)
    → [process-meta]→ parses META header, sets title/tags/etc. (modifies in place)
    → [compute-dates]→ sets article date from META / path / mtime (modifies in place)
    → [build-article-pages]   → PageSkrap (one per published article)
    → [build-date-archives]   → PageSkrap (year + month archive pages)
    → [build-topic-archives]  → PageSkrap (one per tag/topic)
    → [build-main-page]       → PageSkrap (main index, N most recent)
    → [write-html]  → writes .html files to output directory
filesystem
```

## File map

| Path | What it is |
|------|-----------|
| `genblog` | Entry point.  Parses CLI args, opens DB, registers plugins, calls orchestrator. |
| `SCHEMA/skrap.sql` | `skrap` table: id, name, type, owner\_id, last\_modified |
| `SCHEMA/meta.sql` | `meta` table: key/value metadata attached to a skrap |
| `SCHEMA/plugin.sql` | `plugin` table: maps plugin name → integer id |
| `SCHEMA/plugin_meta.sql` | `plugin_meta` table: per-plugin key/value store |
| `cloxsom/skrap.py` | `Skrap` base class + concrete types (`FileSkrap`, `ArticleSkrap`, `PageSkrap`, `TestSkrap`).  Includes a type registry (`register_skrap_type` / `get_skrap_class`). |
| `cloxsom/db.py` | `DB` class — SQLite wrapper.  CRUD for skrap objects and metadata, plugin registration. Metadata values are JSON-serialised for complex types. |
| `cloxsom/orchestrator.py` | `PluginOrchestrator` — builds dependency graph from plugin `inputs()`/`outputs()` declarations, topological-sorts, then calls `plugin.run()` in order. |
| `cloxsom/plugin/plugin.py` | `Plugin` abstract base class.  Subclasses implement `name()`, `inputs()`, `outputs()`, `run()`. |
| `cloxsom/plugins/scanfiles.py` | Walks `articles/` directory, creates one `FileSkrap` per file. |
| `cloxsom/plugins/readfiles.py` | Reads each `FileSkrap` file from disk, creates an `ArticleSkrap` with `original_content`. |
| `cloxsom/plugins/notyet.py` | Marks articles unpublished if a matching `.notyet` file exists. |
| `cloxsom/plugins/process_meta.py` | Strips and parses the `META` header block (Blosxom format).  Sets `title`, `tags`, etc. on the `ArticleSkrap`. |
| `cloxsom/plugins/compute_dates.py` | Determines publication date from META field, path (`/YYYY/MM/DD/`), or file mtime. |
| `cloxsom/plugins/build_article_pages.py` | Creates one `PageSkrap` per published article (`page_type=single`). |
| `cloxsom/plugins/build_date_archives.py` | Creates year and month archive `PageSkrap` objects. |
| `cloxsom/plugins/build_topic_archives.py` | Creates one `PageSkrap` per tag/topic. |
| `cloxsom/plugins/build_main_page.py` | Creates the main-index `PageSkrap` with the N most recent articles. |
| `cloxsom/plugins/write_html.py` | Reads all `PageSkrap` objects and writes HTML files to `output/`.  Templates are currently inline strings — they will become Jinja2 files |
| `cloxsom/meta.py` | Thin `Meta(dict)` subclass — not much here yet. |
| `cloxsom/article.py` | Old draft `Article` class — buggy, predates the current skrap approach; not currently used. |
| `cloxsom/context.py` | Intentionally stubbed `Context` class — abandoned in favour of direct DB queries. |
| `notes/PLAN` | Design notes from 2022–2023.  Good background reading. |
| `notes/old/` | Earlier design notes (FLOW, PLUGINS, PLUGINS\_NEEDED). |

## Known bugs / gaps in the claude draft

1. **Config not passed to plugins** — `genblog` parses `--input`, `--output`,
   `--recent` but the orchestrator only passes `db` to plugin constructors, so
   plugins always use hardcoded defaults (`articles/`, `output/`, 12).

2. **`article.py` is dead code** — predates the current design; has its own bugs.
   Should be deleted or rewritten as a plugin.

3. **No feed generation** — no RSS or Atom plugin yet.

4. **HTML templates are hardcoded strings** in `write_html.py` — later they will be Jinja2 template files

5. **No asset handling** — images, CSS, JS in the articles directory are ignored.

6. **Tag deduplication** — `build_topic_archives` can double-count articles with
   overlapping tag fields (`tags`, `topic`, `category`).

7. **Full regeneration only** — every run recreates all skrap objects from scratch;
   no incremental update.

## Rename

The package was renamed from `suxsom` → `cloxsom` (matching the project name
Closxom).
