# Lense Libraries
from lense.common.utils import valid, invalid, mod_has_class

class RequestHandler(object):
    """
    Base class inherited by all request handlers.
    """
    valid         = valid
    invalid       = invalid
    mod_has_class = mod_has_class