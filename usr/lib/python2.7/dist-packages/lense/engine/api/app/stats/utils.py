from lense.common.utils import valid, invalid, set_response
from lense.engine.api.app.stats.models import DBStatsRequest

def log_request_stats(params):
    """
    Helper method for logging request stats.
    """
    DBStatsRequest(**params).save()

class RequestGet:
    """
    Retrieve API request statistics.
    """
    def __init__(self, parent):
        self.api = parent
        
    def launch(self):
        """
        Worker method for retrieving API request statistics.
        """
        return valid(set_response(DBStatsRequest.objects.all().values(), '[]'))