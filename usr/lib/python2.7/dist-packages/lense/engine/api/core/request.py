from time import time
from sys import getsizeof
from json import loads as json_loads

# Lense Libraries
from lense import import_class
from lense.common.exceptions import RequestError, EnsureError, AuthError
from lense.engine.api.handlers.stats import log_request_stats
from lense.common.utils import RMapValidate, valid, invalid

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
        
        # Set request / API logger / SocketIO data / ACL gateway
        LENSE.REQUEST.set(request)
        LENSE.API.create_logger()
        LENSE.connect_socket().set()
        LENSE.AUTH.init_acl()
    
        # Request map
        self.map = LENSE.API.map_request()
    
        # Authenticate the request
        self.authenticate()
    
    def authenticate(self):
        """
        Authenticate the API request.
        """
        LENSE.LOG.info('Authenticating API user: {0}, group={1}'.format(LENSE.REQUEST.USER.name, repr(LENSE.REQUEST.USER.group)))
        handler_path = '{0}:{1}'.format(LENSE.REQUEST.method, LENSE.REQUEST.path)
        
        # Anonymous request
        if LENSE.REQUEST.is_anonymous:
            return LENSE.REQUEST.ensure(self.map['anon'],
                error = 'Request handler <{0}> does not support anonymous requests'.format(handler_path),
                log   = 'Processing anonymous request for <{0}>'.format(),
                code  = 401)
            
        # Token request
        if LENSE.REQUEST.is_token:    
            return LENSE.REQUEST.ensure(LENSE.OBJECTS.USER.authenticate(),
                error = 'Token request failed',
                log   = 'Token request OK for {0}'.format(LENSE.REQUEST.USER.name),
                code  = 401)
            
        # Authenticated request
        LENSE.REQUEST.ensure(LENSE.OBJECTS.USER.authenticate(),
            error = LENSE.OBJECTS.USER.auth_error,
            log   = 'Authentication successful for user {0}'.format(LENSE.REQUEST.USER.name),
            code  = 401)
        
        # Authorized request handler access
        LENSE.AUTH.ACL.request()
    
    def run(self):
        """
        Worker method for processing the incoming API request.
        """
        req_received = int(round(time() * 1000))
        
        # Request map validator: disable for now, needs an overhaul
        #RMapValidate(self.map['rmap']).validate(LENSE.REQUEST.data)
        
        # Set up the request handler and get a response
        response = import_class(self.map['class'], self.map['module']).launch()
        
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
        
        # OK
        return LENSE.API.LOG.success(response.message, response.data)
    
    @staticmethod
    def dispatch(request):
        """
        Static method for dispatching the request object to the RequestManager.
        
        :param request: The incoming Django request object
        :type  request: HttpRequest
        """
        try:
            manager = RequestManager(request)
            return manager.run()
        
        # Internal request error
        except (EnsureError, RequestError, AuthError) as e:
            LENSE.LOG.exception(e.message)
            return LENSE.HTTP.error(e.message, e.code)