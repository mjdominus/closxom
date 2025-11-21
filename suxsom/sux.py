
import time

# Global registry of Sux types
_SUX_TYPE_REGISTRY = {}

def register_sux_type(sux_class):
    """Register a Sux subclass in the type registry."""
    type_name = sux_class.typ()
    _SUX_TYPE_REGISTRY[type_name] = sux_class
    return sux_class

def get_sux_class(type_name):
    """Get the Sux subclass for a given type name."""
    if type_name not in _SUX_TYPE_REGISTRY:
        raise ValueError(f"Unknown sux type: {type_name}")
    return _SUX_TYPE_REGISTRY[type_name]

class Sux():
    """Base class for all products stored in the database.

    A Sux represents a "product" - something created during blog generation.
    Products can be input files, articles, pages, menus, etc.

    Attributes:
        id: Database ID (None if not yet persisted)
        type: Product type string (from typ() classmethod)
        name: Unique name for this product (within owner)
        owner: Name of the plugin that created this product
        meta: Dictionary of metadata
        last_modified: Unix timestamp of last modification
    """

    @classmethod
    def typ(cls):
        """Return the type string for this Sux subclass.

        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"Sux subclass {cls} must implement typ()")

    def __init__(self, name, owner, meta=None, last_modified=None, id=None):
        """Create new sux object (not yet persistent).

        Args:
            name: Unique name for this product
            owner: Name of the plugin that owns this product
            meta: Optional metadata dictionary
            last_modified: Optional timestamp (defaults to current time)
            id: Optional database ID (for loaded objects)
        """
        self.id = id
        self.type = self.typ()
        self.name = name
        self.owner = owner
        self.set_last_modified(last_modified)
        if meta is None:
            meta = {}
        self.meta = meta

    def persist(self, db):
        """Save this sux to the database."""
        return db.save_sux(self)

    def set_last_modified(self, last_modified=None):
        """Set the last_modified timestamp.

        Args:
            last_modified: Unix timestamp, or None to use current time
        """
        if last_modified is None:
            self.last_modified = time.time()
        else:
            self.last_modified = last_modified

    def __str__(self):
        return f"<sux #{self.id} ({self.type}) '{self.name}' from '{self.owner}'>"

    def __repr__(self):
        return self.__str__()


# ==================== Concrete Sux types ====================

@register_sux_type
class FileSux(Sux):
    """Represents a file found by scanfiles.

    Metadata keys:
        path: Full filesystem path
        relpath: Path relative to blog root
    """
    @classmethod
    def typ(cls):
        return "file"


@register_sux_type
class ArticleSux(Sux):
    """Represents a blog article.

    Metadata keys:
        content: Raw article content (after META removal)
        title: Article title
        date: Publication date
        tags: List of tags
        published: Whether article should be published
        path: Original file path
    """
    @classmethod
    def typ(cls):
        return "article"


@register_sux_type
class PageSux(Sux):
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


# Test sux for test suite
@register_sux_type
class TestSux(Sux):
    @classmethod
    def typ(cls):
        return "test"
