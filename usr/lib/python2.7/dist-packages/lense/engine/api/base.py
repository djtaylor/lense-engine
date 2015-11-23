import re
import copy
import json
import importlib

# Django Libraries
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense.common import LenseCommon
from lense.engine.api.core.mailer import APIEmail
from lense.engine.api.core.logger import APILogger
from lense.engine.api.core.socket import SocketResponse
from lense.common.objects.manager import ObjectsManager

# Lense Common
LENSE = LenseCommon('ENGINE')

class APIBare(object):
    """
    APIBare
    
    Bare-bones base API object mainly used when running utilities from a script,
    the bootstrap module for example.
    """
    def __init__(self, path=None, data=None, method='GET', host='localhost'):
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
        
        # Request object / data / email handler
        self.request = self._get_request()
        self.data    = data
        self.email   = APIEmail()
        
        # API logger
        self.log     = APILogger(self)
        
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

class APIBase(object):
    """
    APIBase
    
    Base class in the inheritance model used by all API utilties assigned to a path, and a
    handful of other class definitions. This class contains common attributes used by all API
    utilities, such as the logger, path details, external utilities, request attributes, etc.
    """
    def __init__(self, request=None, utils=False, acl=None):
        """
        Initialize the APIBase class.
        
        @param request:  The request object from RequestManager
        @type  request:  RequestObject
        @param utils:    Any external utilities required by this API path
        @type  utils:    list
        @param acl:      The ACL gateway generated during request initialization
        @type  acl:      ACLGateway
        """
        
        # Request object / data / path / email handler
        self.request      = request
        self.data         = request.data
        self.path         = request.path
        self.method       = request.method
        self.email        = APIEmail()
        
        # Request handler / objects manager / ACL gateway
        self.handler      = None
        self.objects      = ObjectsManager()
        self.acl          = acl

        # SocketIO client / web socket object
        self.socket       = SocketResponse().construct()
        self.websock      = None
        
    def _set_websock(self):
        """
        Check if the client is making a request via the Socket.IO proxy server.
        """
        if 'socket' in self.request.data:
            
            # Log the socket connection
            LENSE.LOG.info('Received connection from web socket client: {}'.format(str(self.request.data['socket'])))
            
            # Set the web socket response attributes
            self.websock = self.socket.set(self.request.data['socket'])
        else:
            self.websock = None
        
    def get_logger(self, client):
        """
        Return an instance of the APILogger for non-utility classes.
        
        @param client: The IP address of the API client
        @type  client: str
        """
        self.log = APILogger(self, client)
        return self
        
    def construct(self):
        """
        Construct and return the APIBase class.
        """
        
        # Check if a web socket is making an API call
        self._set_websock()
        
        # Set the logger object
        self.log = APILogger(self)
        
        # Return the constructed API object, ready for authentication or other requests
        return LENSE.VALID(self)