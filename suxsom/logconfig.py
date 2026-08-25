"""Central logging configuration for suxsom.

Call configure() once at process startup (genblog, run-plugin, etc.).
Plugins get their logger automatically via Plugin.__init__ and need
no logging setup of their own.
"""

import logging


def configure(level=logging.WARNING):
    """Attach a stderr handler to the suxsom logger tree.

    All plugin loggers are named "suxsom.plugin.<name>" and propagate
    up to "suxsom", so this is the only place output is configured.
    """
    logger = logging.getLogger("suxsom")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
