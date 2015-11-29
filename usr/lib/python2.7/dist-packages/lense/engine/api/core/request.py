from time import time
from sys import getsizeof
from json import loads as json_loads

# Lense Libraries
from lense import import_class
from lense.common.auth.acl import AuthACLGateway
from lense.engine.api.handlers.stats import log_request_stats
from lense.common.utils import JSONTemplate, valid, invalid

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
        return RequestManager.dispatch(request)
    
    # Critical server error
    except Exception as e:
        return LENSE.HTTP.exception()
  
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
        LENSE.REQUEST.set(request)
    
        # API parameters
        self.api_name  = None
        self.api_mod   = None
        self.api_class = None
        self.api_anon  = False
        
        # API base object
        self.api_base  = None
    
        # ACL gateway
        self.gateway   = None
    
    def _authenticate(self):
        """
        Authenticate the API request.
        """
        
        # Log the user and group attempting to authenticate
        LENSE.LOG.info('Authenticating API user: {0}, group={1}'.format(LENSE.REQUEST.USER.name, repr(LENSE.REQUEST.USER.group)))
        
        # Anonymous request
        if LENSE.REQUEST.is_anonymous:
            if not self.api_anon:
                return LENSE.HTTP.error(error='API handler <{0}.{1}> does not support anonymous requests'.format(self.api_mod, self.api_class))
            
        # Token request
        elif LENSE.REQUEST.is_token:    
            if not LENSE.USER.AUTHENTICATE():
                return LENSE.HTTP.error(error=LENSE.USER.AUTH_ERROR, status=401)
            LENSE.LOG.info('API key authentication successfull for user: {0}'.format(LENSE.REQUEST.USER.name))
        
        # Authenticated request
        else:
            if not LENSE.USER.AUTHENTICATE():
                return LENSE.HTTP.error(error=LENSE.USER.AUTH_ERROR, status=401)
            LENSE.LOG.info('API token authentication successfull for user: {0}'.format(LENSE.REQUEST.USER.name))
            
            # Perform ACL authorization
            self.gateway = ACLGateway(LENSE.REQUEST)
        
            # If the user is not authorized for this endpoint/object combination
            if not self.gateway.authorized:
                return LENSE.HTTP.error(error=self.gateway.auth_error, status=401)
    
    def _validate(self):
        """
        Perform initial validation of the request.
        """
    
        # Map the path to a module, class, and API name
        map = LENSE.API.map_request()
        
        # Request map failed
        if not map['valid']: return map['content']
    
        # Validate the request data
        request_err = JSONTemplate(map['content']['rmap']).validate(LENSE.REQUEST.data)
        if request_err:
            return LENSE.HTTP.error(error=request_err, status=400)
    
        # Set the handler objects
        self.api_path    = map['content']['path']
        self.api_mod     = map['content']['mod']
        self.api_class   = map['content']['class']
        self.api_anon    = map['content']['anon']
    
    def run(self):
        """
        Worker method for processing the incoming API request.
        """
        
        # Request received timestamp
        req_received = int(round(time() * 1000))
        
        # Validate and authenticate the request the request
        try:
            validate_error = self._validate()
            auth_error     = None if validate_error else self._authenticate()
            
        # Critical error during validation / authentication
        except Exception as e:
            return LENSE.HTTP.exception()
        
        # Validation / authentication error
        if validate_error: return validate_error
        if auth_error: return auth_error
        
        # Set up the API base
        try:
            
            # Create an instance of the APIBase and run the constructor
            api_obj = LENSE.API.BASE(request=self.request, acl=self.gateway)
            
            # Make sure the construct ran successfully
            if not api_obj['valid']:
                return api_obj['content']
            
            # Set the API base object for endpoint utilities
            self.api_base = api_obj['content']
            
        # Failed to setup the APIBase
        except Exception as e:
            return LENSE.HTTP.exception()
            
        # Load the handler
        handler = import_class(self.api_class, self.api_mod, args=[self.api_base])
        
        # Launch the request handler and return the response
        try:
            response = handler.launch()
            
        # Critical error when running handler
        except Exception as e:
            return LENSE.HTTP.exception()
        
        # Close any open SocketIO connections
        self.api_base.socket.disconnect()
        
        # Response sent timestamp
        rsp_sent = int(round(time() * 1000))
        
        # Log the request
        log_request_stats({
            'path': LENSE.REQUEST.path,
            'method': LENSE.REQUEST.method,
            'client_ip': LENSE.REQUEST.client,
            'client_user': LENSE.REQUEST.USER.name,
            'client_group': LENSE.REQUEST.USER.group,
            'endpoint': LENSE.REQUEST.host,
            'user_agent': LENSE.REQUEST.agent,
            'retcode': int(response['code']),
            'req_size': int(LENSE.REQUEST.size),
            'rsp_size': int(getsizeof(response['content'])),
            'rsp_time_ms': rsp_sent - req_received
        })
        
        # Return either a valid or invalid request response
        if response['valid']:
            return self.api_base.log.success(response['content'], response['data'])
        return self.api_base.log.error(code=response['code'], log_msg=response['content'])
    
    @staticmethod
    def dispatch(request):
        """
        Static method for dispatching the request object to the RequestManager.
        
        :param request: The incoming Django request object
        :type  request: HttpRequest
        """
        manager = RequestManager(request)
        return manager.run()