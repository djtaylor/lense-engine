import json

# Lense Libraries
from lense.common.utils import valid, invalid, rstring
from lense.common.objects.user.models import APIUserKeys, APIUser

class APIKey(object):
    """
    API class used to handle validating, retrieving, and generating API keys.
    """
    def create(self):
        """
        Generate a 64 character API key.
        """
        return rstring(64)

    def _get_api_key(self, id):
        """
        Retrieve the API key for a user or host account.
        """
        
        # Check if the user exists
        api_user = APIUser.objects.filter(username=id).count()
        if not api_user:
            return invalid('Authentication failed, account [{}] not found'.format(id))

        # Make sure the user is enabled
        user_obj = APIUser.objects.get(username=id)
        if not user_obj.is_active:
            return invalid('Authentication failed, account [{}] is disabled'.format(id))
        
        # Return the API key row
        api_key_row = list(APIUserKeys.objects.filter(user=user_obj.uuid).values())

        # User has no API key
        if not api_key_row: 
            return invalid('Authentication failed, no API key found for account [{}]'.format(id))
        return valid(api_key_row[0]['api_key'])

    def validate(self, request):
        """
        Validate the API key for a user or host account.
        """
        
        # Get the API key of the user or host
        api_key = self._get_api_key(id=request.user)
        
        # User has no API key
        if not api_key['valid']: 
            return api_key
            
        # Invalid API key
        if api_key['content'] != request.key:
            return invalid('Client [{0}] has submitted an invalid API key'.format(request.user))
        
        # API key looks OK
        return valid(request)

    def get(self, id):
        """
        Get the API key of a user or host account.
        """
        
        # Get the API key of the user or host
        db_api_key = self._get_api_key(id=id)
        
        # User has no API key
        if not db_api_key: 
            return False
        
        # Return the client API key
        return api_key_row[0]['api_key']