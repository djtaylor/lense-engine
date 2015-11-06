import re
from django.db.models import Q

# Lense Libraries
from lense.common.utils import valid, invalid, set_response
from lense.engine.api.app.stats.models import DBStatsRequest

def log_request_stats(params):
    """
    Helper method for logging request stats.
    """
    DBStatsRequest(**params).save()

class StatsRequestGet:
    """
    Retrieve API request statistics.
    
    GET http://apiserver.mydomain.com/stats/requests
    
    OPTIONAL PARAMETERS:
    - path=/some/path
    - method=GET|POST|PUT|DELETE
    - client_ip=xxx.xxx.xxx.xxx
    - client_user=<username>
    - client_group=<group_uuid>
    - endpoint=<api_server>
    - user_agent=<user_agent_string>
    - retcode=200|500|404|...
    - req_size=gt:<size_bytes>;lt:<size_bytes>;
    - rsp_size=gt:<size_bytes>;lt:<size_bytes>;
    - rsp_time_ms=gt:<time_ms>;lt:<time_ms>;
    - from=<timestamp>
    - to=<timestamp>
    """
    def __init__(self, parent):
        self.api = parent
        
        # Define filters
        self._filters = {}
        
        # Filter keys
        self._filter_keys = {
            'generic': ['path', 'method', 'client_ip', 'client_user', 'client_group', 'endpoint', 'user_agent', 'retcode'],
            'range': ['req_size', 'rsp_size', 'rsp_time_ms']
        }
        
    def _filter_range(self, key):
        """
        Range filter method.
        """
        range_data = self.api.data['key']
        
        # Look for an upper and lower bound
        gt  = None if not 'gt:' in range_data else re.compile(r'^.*gt:([^;]*);.*$').sub(r'\g<1>', range_data)
        lt  = None if not 'lt:' in range_data else re.compile(r'^.*lt:([^;]*);.*$').sub(r'\g<1>', range_data)
        
        # If upper and lower bound set
        if gt and lt:
            self._filters[key] = [Q(**{'{0}__gt'.format(key):gt}) & Q(**{'{0}__lt'.format(key):lt})]
            
        else:
            
            # Upper bound only
            if gt:
                self._filters[key] = Q(**{'{0}__gt'.format(key):gt})
                
            # Lower bound only
            if lt:
                self._filters[key] = Q(**{'{0}__lt'.format(key):lt})
        
    def _filter_generic(self, key):
        """
        Generic filter method for single or multiple key values.
        """
        if key in self.api.data:
            key_data = self.api.data[key]
        
            # Multiple filter values
            if '|' in key_data:
                self._filters[key] = [Q(**{key:v}) for v in key_data.split('|')]
            
            # Single filter value
            else:
                self._filters[key] = key_data
        
    def _run_range_filters(self):
        """
        Value range filters.
        """
        for k in self._filter_keys['range']:
            self._filter_range(k)
        
    def _run_generic_filters(self):
        """
        Generic key/value filters
        """
        for k in self._filter_keys['generic']:
            self._filter_generic(k)
        
    def launch(self):
        """
        Worker method for retrieving API request statistics.
        """
        return valid(set_response(DBStatsRequest.objects.filter(**self._filters).values(), '[]'))