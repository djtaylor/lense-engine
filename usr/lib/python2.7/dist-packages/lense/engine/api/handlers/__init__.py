from os import path
from re import match
from uuid import uuid4

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.utils import mod_has_class, rstring

class RequestOK(object):
    """
    Construct a basic response object for passing back to 
    the request handler.
    """
    def __init__(self, message, data):
        self.message = message
        self.data    = data

class RequestHandler(object):
    """
    Parent class for defining common/shortcut methods for request handlers.
    """
    def __init__(self):
        self.obj    = LENSE.OBJECTS.HANDLER.get(path=LENSE.REQUEST.path,method=LENSE.REQUEST.method)
        self.logpre = '<HANDLERS:{0}:{1}@{2}>'.format(
            self.__class__.__name__, 
            LENSE.REQUEST.USER.name, 
            LENSE.REQUEST.client
        )
    
        # Objects map
        self.objmap = LENSE.REQUEST.path.upper()
    
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
    
    def log(self, msg, level='info'):
        """
        Log wrapper per handler.
        """
        logger = getattr(LENSE.LOG, level, 'info')
        logger('{0} {1}'.format(self.logpre, msg))
    
    def mod_has_class(self, mod, cls, **kwargs):
        """
        Wrapper method for checking if a module contains a class.
        """
        return mod_has_class(mod, cls, **kwargs)
    
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
    
    def ok(self, message='Request successfull', data={}, acl=True, dump=True, process=True):
        """
        Request was successfull, return a response object.
        """
        def not_empty(objects):
            return 
        
        self.ensure(True if (data) else False, 
            isnot = False,
            code  = 404, 
            error = 'Could not find any objects!')
        return RequestOK(message, LENSE.OBJECTS.process(data, acl=acl, dump=dump, noop=not process))
    
    def get_objects(self, acl=True, dump=True, filter={}):
        """
        Helper method for retrieving handler specific objects.
        """
        LENSE.LOG.info('GET_OBJECTS:filter: {0}'.format(filter))
        return getattr(LENSE.OBJECTS, self.objmap).set(acl=acl, dump=dump, count=LENSE.REQUEST.count).get(**filter)
    
    def get_data(self, key, default=None, required=True):
        """
        Retrieve data from the request object. Key parameter can either
        be a single key, or multiple keys delimited by a forward slash.
        
        :param      key: The key(s) to get
        :type       key: str
        :param  default: The default value to return if the key is not found
        :type   default: mixed
        :param required: Through a RequestError if missing
        :type  required: bool
        :rtype: mixed
        """
        retval = default
        
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
            retval = _walk_data(key.split('/'), LENSE.REQUEST.data)
        
        # Single key
        else:
            retval = LENSE.REQUEST.data.get(key, default)
    
        # If the key is required and missing
        if required:
            self.ensure(retval,
                error = 'Missing value for required key: {0}'.format(key),
                debug = 'Required key "{0}" present'.format(key),
                code  = 400)
        return retval
    
    def ensure(self, *args, **kwargs):
        """
        Wrapper method for LENSE.REQUEST.ensure()
        """
        
        # Prepend log prefix
        for k in ['debug', 'error', 'log']:
            if k in kwargs:
                kwargs[k] = '{0} {1}'.format(self.logpre, kwargs[k])
        return LENSE.REQUEST.ensure(*args, **kwargs)