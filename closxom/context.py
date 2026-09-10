
class SkrapNotFound(Exception):
    pass

class Context():
    """A Context seems to be an in-memory list of products.
    Don't need it, get rid of it.  Just query the fucking database.

    Or maybe this is a wrapper providing a more abstract
    API for the  database object?
    """

    def __init__(self):
        raise Exception("Why aren't you just using the database?")

    def failed(self, fail_ok, msg):
        if fail_ok:
            return None
        else:
            raise SkrapNotFound(msg)

    def find_by_name(self, owner, name, fail_ok=True):
        for skrap in self.i:
            if skrap.owner == owner and self.name == name:
                return skrap
        return self.failed(fail_ok, f"Context has no skrap '{name}' owned by '{owner}'")

    def find_by_owner(self, owner):
        found = [ skrap for skrap in self.i if skrap.owner == owner ]
        return found

    def find_by_types(self, types):
        found = [ skrap for skrap in self.i if skrap.type in types ]
        return found
