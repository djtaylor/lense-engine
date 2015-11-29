# Django Libraries
from django.test.client import RequestFactory

# Lense Libraries
from lense.common.http import HTTP_GET
from lense.engine.api.core.mailer import APIEmail
from lense.engine.api.core.logger import APILogger

class APIBare(object):
    """
    APIBare
    
    Bare-bones base API object mainly used when running utilities from a script,
    the bootstrap module for example.
    """
    def __init__(self, path=None, data=None, method=HTTP_GET, host='localhost'):
        """
        Initialize the APIBaseBare class.
        
        @param path:   The API request path
        @type  path:   str
        @param data:   The API request data
        @type  data:   dict
        @param method: The API request method
        @param type:   str
        @param host:   The host to submit the request
        @type  host:   str
        """
        
        # Request path / method / host
        self.path    = path
        self.method  = method
        self.host    = host
        
        # Request object / data
        self.request = self._get_request()
        self.data    = data
        
        # API logger / email handler
        self.log     = APILogger(self)
        self.email   = APIEmail()
        
    def _get_request(self):
        """
        Generate and return a Django request object.
        """
        
        # Define the request defaults
        defaults = {
            'REQUEST_METHOD': self.method,
            'SERVER_NAME':    self.host,
            'PATH_INFO':      '/{}'.format(self.path),
            'REQUEST_URI':    '/api/{}'.format(self.path),
            'SCRIPT_NAME':    '/api',
            'SERVER_PORT':    '10550',
            'CONTENT_TYPE':   'application/json'
        }
        
        # Create a new instance of the request factory
        rf = RequestFactory(**defaults)
        
        # Construct and return the request object
        return rf.request()