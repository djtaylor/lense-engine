import os
import re
import json
import importlib

# Django Libraries
from django.http import HttpResponse, HttpResponseServerError

# Lense Libraries
from lense import PKG_ROOT
from lense.common import config
from lense.common import logger
from lense.engine.api.base import APIBase
from lense.common.http import HEADER, PATH, JSONError, JSONException, HTTP_GET
from lense.common.utils import JSONTemplate
from lense.engine.api.auth.key import APIKey
from lense.common.utils import valid, invalid, truncate
from lense.engine.api.auth.acl import ACLGateway
from lense.engine.api.auth.token import APIToken
from lense.engine.api.app.user.models import DBUser
from lense.engine.api.app.gateway.models import DBGatewayUtilities

# Configuration / Logger
CONF = config.parse('SERVER')
LOG  = logger.create(__name__, CONF.server.log)

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
  
class RequestObject(object):
    """
    Extract and construct information from the Django request object.
    """
    def __init__(self, request):
    
        # Store the raw request object
        self.RAW         = request
        
        # Request data / method / headers / path / client address
        self.method      = request.META['REQUEST_METHOD']
        self.headers     = request.META
        self.path        = request.META['PATH_INFO'][1:]
        self.client      = request.META['REMOTE_ADDR']
        self.data        = self._load_data()
    
        # API authorization attributes
        self.user        = self.headers.get('HTTP_{}'.format(HEADER.API_USER.upper().replace('-', '_')))
        self.group       = self.headers.get('HTTP_{}'.format(HEADER.API_GROUP.upper().replace('-', '_')))
        self.key         = self.headers.get('HTTP_{}'.format(HEADER.API_KEY.upper().replace('-', '_')), '')
        self.token       = self.headers.get('HTTP_{}'.format(HEADER.API_TOKEN.upper().replace('-', '_')), '')
    
        # Debug logging for each request
        self._log_request()
        
    def _log_request(self):
        """
        Helper method for debug logging for each request.
        """
        LOG.info('REQUEST_OBJECT: method={}, path={}, client={}, user={}, group={}, key={}, token={}, data={}'.format(
            self.method,
            self.path,
            self.client,
            self.user,
            self.group,
            self.key,
            self.token,
            truncate(str(self.data))
        ))
    
    def _load_data(self):
        """
        Load request data depending on the method. For POST requests, load the request
        body, for GET requests, load the query string.
        """
    
        # PUT/POST/DELETE requests
        if self.method != HTTP_GET:
            return json.loads(getattr(self.RAW, 'body', '{}'))
        
        # GET requests
        else:
            data = {}
            
            # Store the query string
            query_str = self.RAW.META['QUERY_STRING']
            
            # If the query string is not empty
            if query_str:
                
                # Process each query string key
                for query_pair in self.RAW.META['QUERY_STRING'].split('&'):
                    
                    # If processing a key/value pair
                    if '=' in query_pair:
                        query_set = query_pair.split('=')
                        
                        # Return JSON if possible
                        try:
                            data[query_set[0]] = json.loads(query_set[1])
                            
                        # Non-JSON parseable value
                        except:
                            
                            # Integer value
                            try:
                                data[query_set[0]] = int(query_set[1])
                            
                            # String value
                            except:
                                data[query_set[0]] = query_set[1]
                        
                    # If processing a key flag
                    else:
                        data[query_pair] = True
                        
            # Return the request data
            return data
    
    @staticmethod
    def construct(request):
        """
        Construct and return a Lense request object from a Django request object.
        """
        return RequestObject(request)
  
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
        self.request     = RequestObject.construct(request)
    
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
        LOG.info('Authenticating API user: {}, group={}'.format(self.request.user, repr(self.request.group)))
        
        # Authenticate key for token requests
        if self.request.path == PATH.GET_TOKEN:
            auth_status = APIKey().validate(self.request)
            
            # API key authentication failed
            if not auth_status['valid']:
                return JSONError(error='Invalid API key', status=401).response()
            
            # API key authentication successfull
            LOG.info('API key authentication successfull for user: {}'.format(self.request.user))
            
        # Authenticate token for API requests
        else:
            
            # Invalid API token
            if not APIToken().validate(self.request):
                return JSONError(error='Invalid API token', status=401).response()
            
            # API token looks good
            LOG.info('API token authentication successfull for user: {}'.format(self.request.user))
    
        # Check for a user account
        if DBUser.objects.filter(username=self.request.user).count():
            
            # If no API group was supplied
            if not self.request.group:
                return JSONError(error='Must submit a group UUID using the [api_group] parameter', status=401).response()
            
            # Make sure the group exists and the user is a member
            is_member = False
            for group in DBUser.objects.filter(username=self.request.user).values()[0]['groups']:
                if group['uuid'] == self.request.group:
                    is_member = True
                    break
            
            # If the user is not a member of the group
            if not is_member:
                return JSONError(error='API user [{}] is not a member of group [{}]'.format(self.request.user, self.request.group), status=401).response()
    
    def _validate(self):
        """
        Perform initial validation of the request.
        """
    
        # Map the path to a module, class, and API name
        self.handler_obj = UtilityMapper(self.request.path, self.request.method).handler()
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
        self.api_utils   = self.handler_obj['content']['api_utils']
    
    def handler(self):
        """
        Worker method for processing the incoming API request.
        """
        
        # Validate the request
        try:
            validate_err = self._validate()
            if validate_err:
                return validate_err
            
        # Critical error when validating the request
        except Exception as e:
            return JSONException().response()
        
        # Authenticate the request
        try:
            auth_err     = self._authenticate()
            if auth_err:
                return auth_err
            
        # Critical error when authenticating the request
        except Exception as e:
            return JSONException().response()
        
        # Check the request against ACLs
        acl_gateway = ACLGateway(self.request)
        
        # If the user is not authorized for this endpoint/object combination
        if not acl_gateway.authorized:
            return JSONError(error=acl_gateway.auth_error, status=401).response()
        
        # Set up the API base
        try:
            
            # Create an instance of the APIBase and run the constructor
            api_obj = APIBase(
                request  = self.request, 
                utils    = self.api_utils,
                acl      = acl_gateway
            ).construct()
            
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
        
        # Return either a valid or invalid request response
        if response['valid']:
            return self.api_base.log.success(response['content'], response['data'])
        return self.api_base.log.error(code=response['code'], log_msg=response['content'])
    
class UtilityMapper(object):
    """
    Map a request path to an API utility. Loads the utility request details and map.
    """
    def __init__(self, path=None, method=None):
        """
        Construct the UtilityMapper class.
        
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
        sv = json.loads(open('{}/socket.json'.format(PKG_ROOT), 'r').read())
        
        # Make sure the '_children' key exists
        if not '_children' in j['root']:
            j['root']['_children'] = {}
        
        # Merge the socket parameters map
        j['root']['_children']['socket'] = sv
        j['root']['_optional'].append('socket')
        
    def _build_map(self):
        """
        Load all utility definitions.
        """
        for utility in list(DBGatewayUtilities.objects.all().values()):
            
            # Try to load the request map
            try:
                util_rmap = json.loads(utility['rmap'])
            
                # Map base object
                rmap_base = {
                    'root': util_rmap
                }
                
                # Map to the request path and method
                if (utility['path'] == self.path) and (utility['method'] == self.method):
                
                    # Merge the web socket request validator
                    self._merge_socket(rmap_base)
                
                    # Load the endpoint request handler module string
                    self.map[utility['path']] = {
                        'module': utility['mod'],
                        'class':  utility['cls'],
                        'path':   utility['path'],
                        'desc':   utility['desc'],
                        'method': utility['method'],
                        'utils':  None if not utility['utils'] else json.loads(utility['utils']),
                        'json':   rmap_base
                    }
            
            # Error constructing request map, skip to next utility map
            except Exception as e:
                LOG.exception('Failed to load request map for utility [{}]: {} '.format(utility['path'], str(e)))
                continue
                    
        # All template maps constructed
        return valid(LOG.info('Constructed API utility maps'))
        
    def handler(self):
        """
        Main method for constructing and returning the utility map.
        
        @return valid|invalid
        """
        map_rsp = self._build_map()
        if not map_rsp['valid']:
            return map_rsp
        
        # Request path missing
        if not self.path:
            return invalid(JSONError(error='Missing request path', status=400).response())
        
        # Invalid request path
        if not self.path in self.map:
            return invalid(JSONError(error='Unsupported request path: [{}]'.format(self.path), status=400).response())
        
        # Verify the request method
        if self.method != self.map[self.path]['method']:
            return invalid(JSONError(error='Unsupported request method [{}] for path [{}]'.format(self.method, self.path), status=400).response())
        
        # Get the API module, class handler, and name
        self.handler_obj = {
            'api_mod':   self.map[self.path]['module'],
            'api_class': self.map[self.path]['class'],
            'api_path':  self.map[self.path]['path'],
            'api_utils': self.map[self.path]['utils'],
            'api_map':   self.map[self.path]['json']
        }
        LOG.info('Parsed handler object for API utility [{}]: {}'.format(self.path, self.handler_obj))
        
        # Return the handler module path
        return valid(self.handler_obj)