
# Lense Libraries
from lense.common.utils import valid, invalid

class CallbackHandle:
    """
    Handle requests to the callback URL.
    """
    def __init__(self, parent):
        self.api = parent

        # Callback provider
        self.provider = self.api.data['provider']

    def launch(self):
        """
        Worker method for handling requests to the callback URL.
        """
        self.api.log.info('Processed callback for provider: {0}'.format(self.provider))
        
        # Return a success response
        return valid('Successfully processed callback for provider: {0}'.format(self.provider), {})