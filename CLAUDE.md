# Closxom

Closxom (née suxsom) is a custom static blog generator in Python, replacing a
long-running Blosxom installation. Plugin pipeline over SQLite: every artifact
is a "skrap" (typed product object); `genblog` runs plugins in dependency
order to turn Markdown source articles into static HTML.

See `ARCHITECTURE.md` for the full design and file map, and `TODO.md` for
current architecture direction, unimplemented features, and known bugs.

The package is still named `suxsom` throughout the code; renaming to
`cloxsom` is planned but not done.
