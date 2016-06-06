class RequestOK(object):
    """
    Construct a basic response object for passing back to 
    the request handler.
    """
    def __init__(self, message, data):
        self.message = message
        self.data    = data

class LenseManifest(object):
    """
    Experimental class for parsing a manifest to return handler objects.
    """
    @classmethod
    def mapCommon(cls, path):
        """
        Map manifest commons call.
        """
        paths  = path.split('.')
        retval = LENSE
        for p in paths:
            
            # Root namespace
            if p == 'LENSE':
                continue
            
            # Make sure mapping key exists
            if not hasattr(retval, p):
                LENSE.LOG.error('<mapCommon:{0}> Invalid mapping: {1} in {2}'.format(path, p, repr(retval)))
                return None
            
            # Store the next mapping
            retval = getattr(retval, p)
        return retval
    
    @classmethod
    def mapResult(cls, obj):
        for path,params in obj.iteritems():
            
            if path.startswith('LENSE.'):
                method = cls.mapCommon(path)
                args   = params.get('args', [])
                kwargs = cls.mapCommon(params.get('kwargs'))
                
                return method(*args, **kwargs)
    
    @classmethod
    def mapEnsure(cls, **kwargs):
        """
        Map manifest arguments to ensure method.
        """
        kwargs['result'] = cls.mapResult(kwargs['result'])
        return cls.ensure(**kwargs)
    
    @classmethod
    def ensure(cls, *args, **kwargs):
        """
        Wrapper method for LENSE.REQUEST.ensure()
        """
        return LENSE.REQUEST.ensure(*args, **kwargs)
    
    @classmethod
    def ok(cls, message='Request successfull', data={}):
        """
        Request was successfull, return a response object.
        """
        cls.ensure(True if (data) else False, 
            isnot = False,
            code  = 404, 
            error = 'Could not find any objects!')
        return RequestOK(message, data)
    
    @classmethod
    def parse(cls, manifest):
        variables = {}

        # Process each manifest stanza        
        for stanza in manifest:
            
            # Return a response
            if stanza['type'] == 'return':
                
                # Return OK
                if "@ok" in stanza:
                    
                    # Ensure response data
                    if "@ensure" in stanza["@ok"]["data"]:
                        
                        return cls.ok(data=cls.ensure(**cls.mapEnsure(stanza["@ok"]["data"]["@ensure"])))
                        