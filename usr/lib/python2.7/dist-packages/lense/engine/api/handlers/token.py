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
        user  = LENSE.REQUEST.USER.name
        token = self.ensure(LENSE.OBJECTS.USER.get_token(user),
            error = 'Could not retrieve token for user: {0}'.format(user),
            debug = 'Retrieved token for user: {0}'.format(user),
            code  = 500)
        
        # Return the token
        return self.valid({'token': token})