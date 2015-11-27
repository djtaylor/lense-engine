import os
import re
import json
import importlib
from time import time
from sys import getsizeof

# Django Libraries
from django.http import HttpResponse, HttpResponseServerError

# Lense Libraries
from lense.common.utils import truncate
from lense.common.utils import JSONTemplate
from lense.engine.api.auth.key import AuthAPIKey
from lense.engine.api.auth.acl import ACLGateway
from lense.engine.api.auth.token import APIToken
from lense.common.objects.user.models import APIUser
from lense.common.objects.handler.models import Handlers
from lense.engine.api.handlers.stats import log_request_stats
from lense.common.http import HEADER, PATH, JSONError, JSONException, HTTP_GET, HTTP_POST, HTTP_PUT

def dispatch(request):
    """
    The entry point for all API requests. Called for all endpoints from the Django
    URLs file. Creates a new instance of the EndpointManager class, and returns any
    HTTP response to the client that opened the API request.
    
    :param request: The Django request object
    :type request: object
    :rtype: object
    """
    try:
        
        # Return the response from the request manager
        return RequestManager(request).handler()
    
    # Critical server error
    except Exception as e:
        return JSONException().response()
  
class RequestManager(object):
    """
    The API request manager class. Serves as the entry point for all API request,
    both for authentication requests, and already authenticated requests. Constructs
    the base API class, loads API utilities, and performs a number of other functions
    to prepare the API for the incoming request.
    
    The RequestManager class is instantiated by the dispatch method, which is called
    by the Django URLs module file. It is initialized with the Django request object.
    """
    def __init__(self, request):
        
        # Construct a request object
        self.request     = LENSE.REQUEST.SET(request)
    
        # Request endpoint handler
        self.handler_obj = None
    
        # API parameters
        self.api_name    = None
        self.api_mod     = None
        self.api_class   = None
    
        # API base object
        self.api_base    = None
    
    def _authenticate(self):
        """
        Authenticate the API request.
        """
        
        # Log the user and group attempting to authenticate
        LENSE.LOG.info('Authenticating API user: {0}, group={1}'.format(self.request.user.name, repr(self.request.user.group)))
        
        # Anonymous request
        if self.request.is_anonymous:
            if not self.api_anon:
                return JSONError(error='API handler <{0}.{1}> does not support anonymous requests'.format(self.api_mod, self.api_class))
            
        # Token request
        elif self.request.is_token:    
            if not LENSE.USER.AUTHENTICATE(self.request.user.name, key=self.request.key, group=self.request.user.group):
                return JSONError(error=LENSE.USER.AUTH_ERROR, status=401).response()
            LENSE.LOG.info('API key authentication successfull for user: {0}'.format(self.request.user.name))
        
        # Authenticated request
        else:
            if not LENSE.USER.AUTHENTICATE(self.request.user.name, token=self.request.token, group=self.request.user.group):
                return JSONError(error=LENSE.USER.AUTH_ERROR, status=401).response()
            LENSE.LOG.info('API token authentication successfull for user: {0}'.format(self.request.user.name))
            
            # Perform ACL authorization
            acl_gateway = ACLGateway(self.request)
        
            # If the user is not authorized for this endpoint/object combination
            if not acl_gateway.authorized:
                return JSONError(error=acl_gateway.auth_error, status=401).response()
    
    def _validate(self):
        """
        Perform initial validation of the request.
        """
    
        # Map the path to a module, class, and API name
        self.handler_obj = RequestMapper(self.request.path, self.request.method).handler()
        if not self.handler_obj['valid']:
            return self.handler_obj['content']
    
        # Validate the request data
        request_err  = JSONTemplate(self.handler_obj['content']['api_map']).validate(self.request.data)
        if request_err:
            return JSONError(error=request_err, status=400).response()
    
        # Set the handler objects
        self.api_path    = self.handler_obj['content']['api_path']
        self.api_mod     = self.handler_obj['content']['api_mod']
        self.api_class   = self.handler_obj['content']['api_class']
        self.api_anon    = self.handler_obj['content']['api_anon']
    
    def handler(self):
        """
        Worker method for processing the incoming API request.
        """
        
        # Request received timestamp
        req_received = int(round(time() * 1000))
        
        # Validate and authenticate the request the request
        try:
            validate_error = self._validate()
            auth_error     = self._authenticate()
            
        # Critical error during validation / authentication
        except Exception as e:
            return JSONException().response()
        
        # Validation / authentication error
        if validate_error: return validate_error
        if auth_error: return auth_error
        
        # Set up the API base
        try:
            
            # Create an instance of the APIBase and run the constructor
            api_obj = LENSE.API.BASE(request=self.request, acl=acl_gateway).construct()
            
            # Make sure the construct ran successfully
            if not api_obj['valid']:
                return api_obj['content']
            
            # Set the API base object for endpoint utilities
            self.api_base = api_obj['content']
            
        # Failed to setup the APIBase
        except Exception as e:
            return JSONException().response()
            
        # Load the handler module and class
        handler_mod   = importlib.import_module(self.api_mod)
        handler_class = getattr(handler_mod, self.api_class)
        handler_inst  = handler_class(self.api_base)
        
        # Launch the request handler and return the response
        try:
            response = handler_inst.launch()
            
        # Critical error when running handler
        except Exception as e:
            return JSONException().response()
        
        # Close any open SocketIO connections
        self.api_base.socket.disconnect()
        
        # Response sent timestamp
        rsp_sent = int(round(time() * 1000))
        
        # Log the request
        log_request_stats({
            'path': self.request.path,
            'method': self.request.method,
            'client_ip': self.request.client,
            'client_user': self.request.user.name,
            'client_group': self.request.user.group,
            'endpoint': self.request.host,
            'user_agent': self.request.agent,
            'retcode': int(response['code']),
            'req_size': int(self.request.size),
            'rsp_size': int(getsizeof(response['content'])),
            'rsp_time_ms': rsp_sent - req_received
        })
        
        # Return either a valid or invalid request response
        if response['valid']:
            return self.api_base.log.success(response['content'], response['data'])
        return self.api_base.log.error(code=response['code'], log_msg=response['content'])
    
class RequestMapper(object):
    """
    Map a request path to an API handler. Loads the handler request details and map.
    """
    def __init__(self, path=None, method=None):
        """
        Construct the RequestMapper class.
        
        @param path:   The request path
        @type  path:   str
        @param method: The request method
        @type  method: str
        """
        self.path   = path
        self.method = method
        self.map    = {}
        
    def _merge_socket(self,j):
        """
        Merge request parameters for web socket request. Used for handling connections
        being passed along by the Socket.IO API proxy.
        """
        
        # Load the socket request validator map
        sv = json.loads(open('{0}/api/base/socket.json'.format(LENSE.PROJECT.TEMPLATES), 'r').read())
        
        # Make sure the '_children' key exists
        if not '_children' in j['root']:
            j['root']['_children'] = {}
        
        # Merge the socket parameters map
        j['root']['_children']['socket'] = sv
        j['root']['_optional'].append('socket')
        
    def _build_map(self):
        """
        Load all handler definitions.
        """
        for handler in list(Handlers.objects.all().values()):
            
            # Try to load the request map
            try:
                util_rmap = json.loads(handler['rmap'])
            
                # Map base object
                rmap_base = {
                    'root': util_rmap
                }
                
                # Map to the request path and method
                if (handler['path'] == self.path) and (handler['method'] == self.method):
                
                    # Merge the web socket request validator
                    self._merge_socket(rmap_base)
                
                    # Load the endpoint request handler module string
                    self.map[handler['path']] = {
                        'module': handler['mod'],
                        'class':  handler['cls'],
                        'path':   handler['path'],
                        'desc':   handler['desc'],
                        'method': handler['method'],
                        'anon':   False if not handler['allow_anon'] else handler['allow_anon'],
                        'json':   rmap_base
                    }
            
            # Error constructing request map, skip to next handler map
            except Exception as e:
                LENSE.LOG.exception('Failed to load request map for handler [{0}]: {1} '.format(handler['path'], str(e)))
                continue
                    
        # All template maps constructed
        return LENSE.VALID(LENSE.LOG.info('Constructed API handler maps'))
        
    def handler(self):
        """
        Main method for constructing and returning the handler map.
        
        @return valid|invalid
        """
        map_rsp = self._build_map()
        if not map_rsp['valid']:
            return map_rsp
        
        # Request path missing
        if not self.path:
            return LENSE.INVALID(JSONError(error='Missing request path', status=400).response())
        
        # Invalid request path
        if not self.path in self.map:
            return LENSE.INVALID(JSONError(error='Unsupported request path: {0}'.format(self.path), status=400).response())
        
        # Verify the request method
        if self.method != self.map[self.path]['method']:
            return LENSE.INVALID(JSONError(error='Unsupported request method "{0}" for path "{1}"'.format(self.method, self.path), status=400).response())
        
        # Get the API module, class handler, and name
        self.handler_obj = {
            'api_mod':   self.map[self.path]['module'],
            'api_class': self.map[self.path]['class'],
            'api_path':  self.map[self.path]['path'],
            'api_map':   self.map[self.path]['json'],
            'api_anon':  self.map[self.path]['anon']
        }
        LENSE.LOG.info('Parsed handler object for API handler "{0}": {1}'.format(self.path, self.handler_obj))
        
        # Return the handler module path
        return LENSE.VALID(self.handler_obj)