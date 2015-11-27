import re
import copy
import json
import importlib

# Django Libraries
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense.common.utils import valid
from lense.engine.api.core.mailer import APIEmail
from lense.engine.api.core.logger import APILogger
from lense.engine.api.core.socket import SocketResponse
from lense.common.objects.manager import ObjectsManager

class APIBase(object):
    """
    APIBase
    
    Base class in the inheritance model used by all API utilties assigned to a path, and a
    handful of other class definitions. This class contains common attributes used by all API
    utilities, such as the logger, path details, external utilities, request attributes, etc.
    """
    def __init__(self, request=None, acl=None):
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
        return valid(self)