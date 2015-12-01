from lense.common.utils import valid
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
        return {
            'token': LENSE.REQUEST.ensure(LENSE.USER.token(), 
                value = str, 
                error = 'Could not retrieve API token for user: {0}'.format(LENSE.REQUEST.USER.name)
            )
        }