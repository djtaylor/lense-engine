from lense.engine.api.handlers import RequestHandler

class Token_Get(RequestHandler):
    """
    Class used to handle token requests.
    """
    def launch(self):
        """
        Worker method used to process token requests and return a token if the API
        key is valid and authorized.
        """
        self.ensure(self.get_data('uuid', False),
            error = 'Could not find user UUID in request data',
            debug = 'Found user UUID in request data',
            code  = 400)
        
        # Return the token if possible
        return self.valid({
            'token': self.ensure(LENSE.OBJECTS.USER.get_token(self.get_data('uuid')), 
                isnot = None, 
                error = 'Could not retrieve API token for user: {0}'.format(LENSE.REQUEST.USER.name),
                debug = 'Retrieved API token for user: {0}'.format(LENSE.REQUEST.USER.name),
                code  = 500
            )
        })