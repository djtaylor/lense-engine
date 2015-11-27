import json

# Lense Libraries
from lense.common.utils import valid, invalid, rstring
from lense.common.objects.user.models import APIUserKeys, APIUser

class AuthAPIKey(object):
    """
    API class used to handle validating, retrieving, and generating API keys.
    """
    def create(self):
        """
        Generate a 64 character API key.
        """
        return rstring(64)

    def get(self, user):
        """
        Get the API key of a user or host account.
        
        :param user: The user account to retrieve the key for
        :type  user: str
        """
        _user = LENSE.USER.GET(user)
        
        # User doesn't exist
        if not _user:
            LENSE.LOG.error('API user "{0}" does not exist in database, authentication failed'.format(user))
            return None
        
        # Make sure the user is enabled
        if not user_obj.is_active:
            LENSE.LOG.error('API user "{0}" is disabled, authentication failed'.format(user))
            return None
        
        # Get the API key
        api_key = list(APIUserKeys.objects.filter(user=user_obj.uuid).values())

        # User has no API key
        if not api_key:
            LENSE.LOG.error('API user "{0}" has no key in the database, authentication failed'.format(user))
            return None
        
        # Returmn the API key
        return api_key[0]['api_key']
    
    @staticmethod
    def validate(user, key):
        """
        Validate the API key for a user or host account.
        
        :param user: The user account to validate
        :type  user: str
        :param  key: The incoming API key to validate
        :type   key: str
        """
        api_key = AuthAPIKey()
        
        # Get the API key of the user
        auth = api_key.get(user=user)
        
        # User has no key
        if not auth: return False
        
        # Invalid key in request
        if not auth == key:
            LENSE.LOG.error('User "{0}" has submitted and invalid API key'.format(user))
            return False
        
        # API key looks OK
        return True