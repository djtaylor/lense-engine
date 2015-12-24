from time import time
from sys import getsizeof
from json import loads as json_loads

# Lense Libraries
from lense import import_class
from lense.common.exceptions import RequestError, EnsureError
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
        
        # Set request / API logger / SocketIO data
        LENSE.REQUEST.set(request)
        LENSE.API.create_logger()
        LENSE.connect_socket().set()
    
        # Request map
        self.map       = None
    
    def _authenticate(self):
        """
        Authenticate the API request.
        """
        LENSE.LOG.info('Authenticating API user: {0}, group={1}'.format(LENSE.REQUEST.USER.name, repr(LENSE.REQUEST.USER.group)))
        
        # Anonymous request
        if LENSE.REQUEST.is_anonymous:
            if not self.map['anon']:
                return LENSE.HTTP.error(msg='API handler <{0}.{1}> does not support anonymous requests'.format(self.map['mod'], self.api_class))
            
        # Token request
        elif LENSE.REQUEST.is_token:    
            if not LENSE.OBJECTS.USER.authenticate():
                return LENSE.HTTP.error(msg=LENSE.OBJECTS.USER.auth_error, status=401)
            LENSE.LOG.info('API key authentication successfull for user: {0}'.format(LENSE.REQUEST.USER.name))
        
        # Authenticated request
        else:
            if not LENSE.OBJECTS.USER.AUTHENTICATE():
                return LENSE.HTTP.error(msg=LENSE.OBJECTS.USER.auth_error, status=401)
            LENSE.LOG.info('API token authentication successfull for user: {0}'.format(LENSE.REQUEST.USER.name))
            
            # Run the request through the ACL gateway
            LENSE.AUTH.set_acl(LENSE.REQUEST)
            
            # Access not authorized
            if not LENSE.AUTH.ACL.authorized:
                return LENSE.HTTP.error(msg=LENSE.AUTH.ACL.auth_error, status=401)
    
    def _validate(self):
        """
        Perform initial validation of the request.
        """
    
        # Map the path to a module, class, and API name
        map = LENSE.API.map_request()
        
        # Request map failed
        if not map['valid']: 
            return map['content']
        self.map = map['content']
    
        # Validate the request data
        request_err = JSONTemplate(self.map['rmap']).validate(LENSE.REQUEST.data)
        if request_err:
            return LENSE.HTTP.error(msg=request_err, status=400)
    
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
            return LENSE.HTTP.exception(str(e))
        
        # Validation / authentication error
        if validate_error: return validate_error
        if auth_error: return auth_error
        
        # Set up the request handler and get a response
        try:       
            response = import_class(self.map['class'], self.map['module']).launch()
            
        # Request error
        except RequestError as e:
            return LENSE.HTTP.error(msg=e.message, status=e.code)
            
        # Ensure error
        except EnsureError as e:
            LENSE.LOG.exception(str(e))
            return LENSE.HTTP.exception()
            
        # Critical error when running handler
        except Exception as e:
            LENSE.LOG.exception(str(e))
            return LENSE.HTTP.exception()
        
        # Close any open SocketIO connections
        LENSE.SOCKET.disconnect()
        
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
            return LENSE.API.LOG.success(response['content'], response['data'])
        return LENSE.API.LOG.error(code=response['code'], log_msg=response['content'])
    
    @staticmethod
    def dispatch(request):
        """
        Static method for dispatching the request object to the RequestManager.
        
        :param request: The incoming Django request object
        :type  request: HttpRequest
        """
        manager = RequestManager(request)
        return manager.run()