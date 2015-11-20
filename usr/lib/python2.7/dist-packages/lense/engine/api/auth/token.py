import datetime

# Django Libraries
from django.conf import settings

# Lense Libraries
from lense.common import LenseCommon
from lense.common.utils import rstring
from lense.common.objects.user.models import APIUser, APIUserTokens

# Lense Common
LENSE = LenseCommon('ENGINE')

class APIToken(object):
    """
    API class used to assist in validating, creating, and retrieving API authentication tokens.
    """
    def _get_api_token(self, id):
        """
        Retrieve the API token for a user or host account.
        """
        
        # Check if the user exists
        api_user = APIUser.objects.filter(username=id).count()
        if not api_user:
            return LENSE.INVALID('Authentication failed, account [{}] not found'.format(id))
            
        # Make sure the user is enabled
        user_obj = APIUser.objects.get(username=id)
        if not user_obj.is_active:
            return LENSE.INVALID('Authentication failed, account [{}] is disabled'.format(id))
        
        # Return the API token row
        api_token_row = list(APIUserTokens.objects.filter(user=user_obj.uuid).values())

        # User has no API key
        if not api_token_row:
            return LENSE.VALID(None)
        return LENSE.VALID(api_token_row[0]['token'])
    
    def create(self, id=None):
        """
        Generate a new API authentication token.
        """
        token_str = rstring(255)
        expires   = datetime.datetime.now() + datetime.timedelta(hours=settings.API_TOKEN_LIFE)
            
        # Create a new API token
        LENSE.LOG.info('Generating API token for client [{}]'.format(id))
        db_token  = APIUserTokens(id = None, user=APIUser.objects.get(username=id), token=token_str, expires=expires)
        db_token.save()
        
        # Return the token
        return token_str
    
    def get(self, id):
        """
        Get the API authentication token for a user or host account.
        """
        LENSE.LOG.info('Retrieving API token for ID [{}]'.format(id))
            
        # Check if the user exists
        api_user  = APIUser.objects.filter(username=id).count()
        
        # Attempt to retrieve an existing token
        api_token = self._get_api_token(id=id)
        
        # If there was an error
        if not api_token['valid']:
            return api_token
        
        # If the user doesn't have a token yet
        if api_token['content'] == None:
            api_token['content'] = self.create(id=id)
        LENSE.LOG.info('Retrieved token for API ID [{}]: {}'.format(id, api_token['content']))
        return api_token['content']
    
    def validate(self, request):
        """
        Validate the API token in a request from either a user or host account.
        """
        
        # Missing API user and/or API token
        if not hasattr(request, 'user') or not hasattr(request, 'token'):
            LENSE.LOG.error('Missing required token validation headers [api_user] and/or [api_token]')
            return False
        LENSE.LOG.info('Validating API token for ID [{}]: {}'.format(request.user, request.token))
            
        # Get the users API token from the database
        db_token = self._get_api_token(id=request.user)

        # If no API token exists yet
        if not db_token['valid']:
            LENSE.LOG.error(db_token['content'])
            return False

        # Make sure the token is valid
        if request.token != db_token['content']:
            LENSE.LOG.error('Client [{}] has submitted an invalid API token'.format(request.user))
            return False
        return True