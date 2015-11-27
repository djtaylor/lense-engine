import datetime

# Django Libraries
from django.conf import settings

# Lense Libraries
from lense.common import LenseCommon
from lense.common.utils import rstring
from lense.common.objects.user.models import APIUser, APIUserTokens

# Lense Common
LENSE = LenseCommon('ENGINE')

class AuthAPIToken(object):
    """
    API class used to assist in validating, creating, and retrieving API authentication tokens.
    """
    def create(self, user=None):
        """
        Generate a new API authentication token.
        
        :param user: The user account to generate the token for
        :type  user: str
        """
        token_str = rstring(255)
        expires   = datetime.datetime.now() + datetime.timedelta(hours=settings.API_TOKEN_LIFE)
            
        # Create a new API token
        LENSE.LOG.info('Generating API token for user: {0}'.format(user))
        db_token  = APIUserTokens(id = None, user=APIUser.objects.get(username=user), token=token_str, expires=expires)
        db_token.save()
        
        # Return the token
        return token_str
    
    def get(self, user):
        """
        Get the API authentication token for a user or host account.
        
        :param user: The user account to retrieve the token for
        :type  user: str
        """
        
        # Check if the user exists
        if not APIUser.objects.filter(username=user).count():
            LENSE.LOG.error('API user "{0}" does not exist in database, authentication failed'.format(user))
            return None

        # Get the user object
        user_obj = APIUser.objects.get(username=user)

        # Make sure the user is enabled
        if not user_obj.is_active:
            LENSE.LOG.error('API user "{0}" is disabled, authentication failed'.format(user))
            return None
        
        # Get the API token
        api_token = list(APIUserKeys.objects.filter(user=user_obj.uuid).values())

        # User has no API key
        if not api_token:
            LENSE.LOG.error('API user "{0}" has no token in the database, authentication failed'.format(user))
            return None
        
        # Returmn the API token
        return api_token[0]['api_token']
    
    @staticmethod
    def validate(user, token):
        """
        Validate the API token in a request from either a user or host account.
        
        :param  user: The user account to validate
        :type   user: str
        :param token: The incoming API token to validate
        :type  token: str
        """
        api_token = AuthAPIToken()
        
        # Get the users API token
        auth = api_token.get(user)
        
        # User has no token
        if not auth: return False
        
        # Invalid API token
        if not auth == token:
            LENSE.LOG.error('User "{0}" has submitted and invalid API token'.format(user))
            return False
        
        # Token looks OK
        return True