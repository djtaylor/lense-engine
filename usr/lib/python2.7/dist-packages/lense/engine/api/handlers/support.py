from lense.engine.api.handlers import RequestHandler

class Support_Get(RequestHandler):
    """
    Retrieve a listing of API capabilities.
    """
    def launch(self):
        """
        Worker method to retrieve a listing of API handlers.
        """
        support  = {}
        
        # Get handlers
        for handler in LENSE.OBJECTS.HANDLER.get_internal():
            support[handler.name] = {
                'uuid': handler.uuid,
                'path': handler.path,
                'method': handler.method,
                'name': handler.name,
                'desc': handler.desc
            }
        
        # Return server capabilities
        return self.ok(data=support)