from six import string_types

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
    def __init__(self, manifest):
        self.manifest  = manifest
        self.variables = {}

    def mapCommon(self, path):
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
    
    def mapResult(self, obj):
        for path,params in obj.iteritems():
            
            if path.startswith('LENSE.'):
                method = self.mapCommon(path)
                args   = params.get('args', [])
                kwargs = self.mapCommon(params.get('kwargs'))
                
                return method(*args, **kwargs)
    
    def mapEnsure(self, **kwargs):
        """
        Map manifest arguments to ensure method.
        """
        kwargs['result'] = self.mapResult(kwargs['result'])
        return kwargs
                
    def ensure(self, *args, **kwargs):
        """
        Wrapper method for LENSE.REQUEST.ensure()
        """
        return LENSE.REQUEST.ensure(*args, **kwargs)
    
    def ok(self, message='Request successfull', data={}):
        """
        Request was successfull, return a response object.
        """
        self.ensure(True if (data) else False, 
            isnot = False,
            code  = 404, 
            error = 'Could not find any objects!')
        return RequestOK(message, data)
    
    def launch(self, manifest):

        # Process each manifest stanza        
        for stanza in self.manifest:
            
            # Store a variable
            if stanza['type'] == 'store':
                self.variables[stanza['key']] = self.map(stanza['map'])
            
            # Execute a method
            if stanza['type'] == 'exec':
                self.map(stanza['map'])
            
            # Return a value
            if stanza['type'] == 'return':
                return self.map(stanza['map'])
                
            # Return a response
            if stanza['type'] == 'response':
                
                # Return OK
                if "@ok" in stanza:
                    
                    # Ensure response data
                    if "@ensure" in stanza["@ok"]["data"]:
                        
                        return self.ok(data=self.ensure(**self.mapEnsure(**stanza["@ok"]["data"]["@ensure"])))
                        