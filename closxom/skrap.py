
import time

# Global registry of Skrap types
_SKRAP_TYPE_REGISTRY = {}

def register_skrap_type(skrap_class):
    """Register a Skrap subclass in the type registry."""
    type_name = skrap_class.typ()
    _SKRAP_TYPE_REGISTRY[type_name] = skrap_class
    return skrap_class

def get_skrap_class(type_name):
    """Get the Skrap subclass for a given type name."""
    if type_name not in _SKRAP_TYPE_REGISTRY:
        raise ValueError(f"Unknown skrap type: {type_name}")
    return _SKRAP_TYPE_REGISTRY[type_name]

class Skrap():
    """Base class for all products stored in the database.

    A Skrap represents a "product" - something created during blog generation.
    Products can be input files, articles, pages, menus, etc.

    Attributes:
        id: Database ID (None if not yet persisted)
        type: Product type string (from typ() classmethod)
        name: Unique name for this product (within owner)
        owner: Name of the plugin that created this product
        meta: Dictionary of metadata
        last_updated: Unix timestamp this record was last written
        content: The skrap's primary payload (article text, generated HTML,
            etc.), as opposed to metadata about that payload. None if this
            skrap has no content of its own.
    """

    @classmethod
    def typ(cls):
        """Return the type string for this Skrap subclass.

        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"Skrap subclass {cls} must implement typ()")

    def __init__(self, name, owner, meta=None, last_updated=None, id=None, content=None):
        """Create new skrap object (not yet persistent).

        Args:
            name: Unique name for this product
            owner: Name of the plugin that owns this product
            meta: Optional metadata dictionary
            last_updated: Optional timestamp (defaults to current time)
            id: Optional database ID (for loaded objects)
            content: Optional primary payload for this skrap
        """
        self.id = id
        self.type = self.typ()
        self.name = name
        self.owner = owner
        self.set_last_updated(last_updated)
        if meta is None:
            meta = {}
        self.meta = meta
        self.content = content

    def set_last_updated(self, last_updated=None):
        """Set the last_updated timestamp (when this record was last written).

        Args:
            last_updated: Unix timestamp, or None to use current time
        """
        if last_updated is None:
            self.last_updated = time.time()
        else:
            self.last_updated = last_updated

    def __str__(self):
        return f"<skrap #{self.id} ({self.type}) '{self.name}' from '{self.owner}'>"

    def __repr__(self):
        return self.__str__()


# ==================== Concrete Skrap types ====================

@register_skrap_type
class FileSkrap(Skrap):
    """Represents a file found by scanfiles.

    Metadata keys:
        path: Full filesystem path
        relpath: Path relative to blog root
    """
    @classmethod
    def typ(cls):
        return "file"


@register_skrap_type
class ArticleSkrap(Skrap):
    """Represents a blog article.

    Metadata keys:
        title: Article title
        tags: List of tags
        published_raw: Raw `published:` META string, owned by process_meta
    """
    @classmethod
    def typ(cls):
        return "article"


@register_skrap_type
class PublicationSkrap(Skrap):
    """Represents an article's publication state, as resolved by
    resolve_publication. Named after (and dependent on) the ArticleSkrap
    it pertains to; has no content of its own.

    Metadata keys:
        pubdate: Parsed publication instant (UTC ISO-8601), or absent
        published: 0/1, recomputed each build from pubdate <= now
    """
    @classmethod
    def typ(cls):
        return "publication"

    def is_published(self):
        return bool(self.meta.get('published'))


@register_skrap_type
class HTMLSkrap(Skrap):
    """Represents an article's rendered-to-HTML body, as produced by the
    formatter plugin. Named after (and dependent on) the ArticleSkrap it
    pertains to. content is the rendered HTML body - never the raw
    Markdown/HTML source.
    """
    @classmethod
    def typ(cls):
        return "html"


@register_skrap_type
class PageSkrap(Skrap):
    """Represents an output page (single article, archive, etc.).

    Metadata keys:
        article_ids: List of article IDs to include on this page
        output_path: Where to write the HTML file
        page_type: Type of page (single, date_archive, topic_archive, main)
        title: Page title
        date: For date archives, the date being archived
        topic: For topic archives, the topic/tag
    """
    @classmethod
    def typ(cls):
        return "page"


# Test skrap for test suite
@register_skrap_type
class TestSkrap(Skrap):
    @classmethod
    def typ(cls):
        return "test"
