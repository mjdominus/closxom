The current logic around `published` is unfortunately quite complicated but has
to be respected to that existing draft articles don't escape into the wild.

Consider a file `article.blog`. 

1. The sentinel file `article.notyet` might exist or not.
2. `article.blog` might have an explicit metadata section with a `published`
   value. If so:
  3. It might be the special constant 0
  4. It might be a unix epoch time
  5. It might be a date in the form YYYY-MM-DD
3. There is a cache of article publication dates. It might have a value for
   `article.blog`.

I think the current logic is:

* If `article.notyet` exists, the article is unpublished.
* Otherwise, if there is an explicit `published: 0`, the article is unpublished.
* If there's an explicit `published` value, parse it and cache it. Otherwise, if
  there is a cached date, use it. If not, cache the file's mtime and use that.

Now there is some date in the cache. If the date is in the future, the article
is unpublished. Otherwise, it is published. 

-----

The complex logic exists because there are two mechanisms for handling
unpublished draft articles. The old way was that anything that doesn't have
`.notyet` is considered published. The new way is that new articles will have an
explicit `published` value in the metadata section. But the old articles were
never converted.

Publication date affects many aspects of the output. For example, it controls
which monthly archive page the article appears on. The main page displays the 12
most recently published articles. The publication date appears on the article's
page. 

When article text is revised, we do not want to update the publication date.
Hence, for old articles, the cache. For new articles, the `published` value in
the metadata is used. To change the publication date, the author would have to
update the metadata and then purge the cache manually, but this never happens.
