from lense.engine.api.app.integrator.models import DBIntegrators

class _IntegratorRunner(object):
    """
    Run the targeted integrator.
    """

class IntegratorMapper(object):
    """
    Map all available integrators
    """
    def __init__(self):
        self._integrators = DBIntegrators.objects.values()
    
    def get(self, path=None, method=None):
        """
        Retrieve a mapped integrator.
        """
        
        # Retrieving all integrators
        if not path and not method:
            return self._integrators
        
        # Search by method 
        if not path and method:
            f = []
            for i in self._integrators:
                if i['method'] == method:
                    f.append(i)
            return f
        
        # Search by path
        if path and not method:
            f = []
            for i in self._integrators:
                if i['path'] == path:
                    f.append(i)
            return f
        
        # Search by path and method
        if path and method:
            for i in self._integrators:
                if (i['path'] == path) and (i['method'] == method):
                    return i
            return None
                