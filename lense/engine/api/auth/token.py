import datetime

# Django Libraries
from django.conf import settings

# Lense Libraries
from lense.common import config
from lense.common import logger
from lense.common.utils import valid, invalid, rstring
from lense.engine.api.app.user.models import DBUserAPITokens, DBUser

class APIToken(object):
    """
    API class used to assist in validating, creating, and retrieving API authentication tokens.
    """
    def __init__(self):
        
        # Configuration / logger objects
        self.conf = config.parse('SERVER')
        self.log  = logger.create(__name__, self.conf.server.log)
    
    def _get_api_token(self, id):
        """
        Retrieve the API token for a user or host account.
        """
        
        # Check if the user exists
        api_user = DBUser.objects.filter(username=id).count()
        if not api_user:
            return invalid('Authentication failed, account [{}] not found'.format(id))
            
        # Make sure the user is enabled
        user_obj = DBUser.objects.get(username=id)
        if not user_obj.is_active:
            return invalid('Authentication failed, account [{}] is disabled'.format(id))
        
        # Return the API token row
        api_token_row = list(DBUserAPITokens.objects.filter(user=user_obj.uuid).values())

        # User has no API key
        if not api_token_row:
            return valid(None)
        return valid(api_token_row[0]['token'])
    
    def create(self, id=None):
        """
        Generate a new API authentication token.
        """
        token_str = rstring(255)
        expires   = datetime.datetime.now() + datetime.timedelta(hours=settings.API_TOKEN_LIFE)
            
        # Create a new API token
        self.log.info('Generating API token for client [{}]'.format(id))
        db_token  = DBUserAPITokens(id = None, user=DBUser.objects.get(username=id), token=token_str, expires=expires)
        db_token.save()
        
        # Return the token
        return token_str
    
    def get(self, id):
        """
        Get the API authentication token for a user or host account.
        """
        self.log.info('Retrieving API token for ID [{}]'.format(id))
            
        # Check if the user exists
        api_user  = DBUser.objects.filter(username=id).count()
        
        # Attempt to retrieve an existing token
        api_token = self._get_api_token(id=id)
        
        # If there was an error
        if not api_token['valid']:
            return api_token
        
        # If the user doesn't have a token yet
        if api_token['content'] == None:
            api_token['content'] = self.create(id=id)
        self.log.info('Retrieved token for API ID [{}]: {}'.format(id, api_token['content']))
        return api_token['content']
    
    def validate(self, request):
        """
        Validate the API token in a request from either a user or host account.
        """
        
        # Missing API user and/or API token
        if not hasattr(request, 'user') or not hasattr(request, 'token'):
            self.log.error('Missing required token validation headers [api_user] and/or [api_token]')
            return False
        self.log.info('Validating API token for ID [{}]: {}'.format(request.user, request.token))
            
        # Get the users API token from the database
        db_token = self._get_api_token(id=request.user)

        # If no API token exists yet
        if not db_token['valid']:
            self.log.error(db_token['content'])
            return False

        # Make sure the token is valid
        if request.token != db_token['content']:
            self.log.error('Client [{}] has submitted an invalid API token'.format(request.user))
            return False
        return True