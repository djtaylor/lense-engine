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
        return self.valid({
            'token': self.ensure(LENSE.USER.token(), 
                isnot = None, 
                error = 'Could not retrieve API token for user: {0}'.format(LENSE.REQUEST.USER.name)
            )
        })