# Lense Libraries
from lense.common.auth import AuthAPIToken
from lense.common.utils import valid, invalid
from lense.engine.api.handlers import RequestHandler

class Token_Get(RequestHandler):
    """
    Class used to handle token requests.
    """
    def __init__(self, parent):
        self.api = parent
        
    def launch(self):
        """
        Worker method used to process token requests and return a token if the API
        key is valid and authorized.
        """
        
        # Target user
        api_user  = LENSE.REQUEST.USER.name
        
        # Get the API token
        api_token = AuthAPIToken.get(api_user)
        
        # Handle token retrieval errors
        if api_token == False:
            return invalid(LENSE.LOG.error('Error retreiving API token for user: {0}'.format(api_user)))
        return valid({'token': api_token})