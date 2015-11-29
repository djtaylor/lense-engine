# Lense Libraries
from lense.common.utils import valid, invalid
from lense.engine.api.auth import AuthAPIToken
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
        
        # Get the API token
        api_token = AuthAPIToken.get(self.api.request.user.name)
        
        # Handle token retrieval errors
        if api_token == False:
            return invalid(self.api.log.error('Error retreiving API token for user: {0}'.format(self.api.request.user.name)))
        else:
            
            # Return the API token
            return valid({'token': api_token})