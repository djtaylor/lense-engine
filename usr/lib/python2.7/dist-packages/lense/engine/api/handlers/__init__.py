from os import path
from re import match
from uuid import uuid4

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.utils import mod_has_class, valid, invalid, rstring

class RequestHandler(object):
    """
    Parent class for defining common/shortcut methods for request handlers.
    """
    def acl_object_supported(self, otype):
        """
        Ensure a particular ACL object type is supported.
        """
        acl_objects = LENSE.OBJECTS.ACL.get_objects()
        
        # Object type is none, supported
        if not otype:
            return True
        
        # Check if the object is supported
        supported = False
        for acl_obj in acl_objects:
            if acl_obj['type'] == object:
                supported = True
                break
        return supported
    
    def rstring(self, *args, **kwargs):
        return rstring(*args, **kwargs)
    
    def valid(self, *args, **kwargs):
        return valid(*args, **kwargs)
    
    def invalid(self, *args, **kwargs):
        return invalid(*args, **kwargs)
    
    def mod_has_class(*args, **kwargs):
        """
        Wrapper method for checking if a module contains a class.
        """
        return mod_has_class(*args, **kwargs)
    
    def is_module(self, m):
        """
        Check if a particular Lense module exists.
        
        :param p: The relative module path to look for
        :type  p: str
        :rtype: bool
        """
        return False if not path.isfile('{0}/{1}.py'.format(MODULE_ROOT, mod.replace('.', '/'))) else True
    
    def in_list(self, k,l):
        """
        Helper method for checking if a specified key is in a list of values.
        
        :param k: The key to look for
        :type  k: str
        :param l: The list to check against
        :type  l: list
        :rtype: bool
        """
        return True if k in l else False
    
    def create_uuid(self):
        """
        Return a UUID4 string.
        """
        return str(uuid4())
    
    def match(self, regex, val):
        """
        Check if a regular expressions matches against a value.
        """
        return match(regex, val)
    
    def clear_data(self, key):
        """
        Clear a key from request data
        
        :param key: The key to delete from request data
        :type  key: str
        """
        if key in LENSE.REQUEST.data:
            del LENSE.REQUEST.data[key]
    
    def get_data(self, key, default=None):
        """
        Retrieve data from the request object. Key parameter can either
        be a single key, or multiple keys delimited by a forward slash.
        
        :param     key: The key(s) to get
        :type      key: str
        :param default: The default value to return if the key is not found
        :type  default: mixed
        :rtype: mixed
        """
        
        def _walk_data(keys, data):
            """
            Recursively walk through the data structure for nested keys.
            
            :param keys: The keys to walk through
            :type  keys: list
            :param data: The current level of data object
            :type  data: dict
            :rtype: str
            """
            current = k[0]
            
            # On the last key
            if len(keys) == 1:
                return d.get(keys, default)
            
            # More keys to go
            else:
                if not current in data:
                    return default
        
                # Go to the next level
                keys.pop(0)
                return _walk_data(keys, data.get(current))
        
        # Nested keys
        if '/' in key:
            return _walk_data(key.split('/'), LENSE.REQUEST.data)
        
        # Single key
        else:
            return LENSE.REQUEST.data.get(key, default)
    
    def ensure(self, *args, **kwargs):
        """
        Wrapper method for LENSE.REQUEST.ensure()
        """
        return LENSE.REQUEST.ensure(*args, **kwargs)