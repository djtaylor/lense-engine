from time import time
from sys import getsizeof
from json import loads as json_loads

# Lense Libraries
from lense import import_class
from lense.common.manifest.interface import ManifestInterface
from lense.common.exceptions import RequestError, EnsureError, AuthError, ManifestError
from lense.engine.api.handlers.stats import log_request_stats

# Request timers
REQ_START = None
REQ_END   = None

class RequestOK(object):
    def __init__(self, message, data):
        self.message = message
        self.data    = data

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
        return LENSE.HTTP.exception(str(e))

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

        # Request map
        self.map = LENSE.API.map_request()

        # Authenticate the request
        self.authenticate()

    def authenticate(self):
        """
        Authenticate the API request.
        """
        LENSE.LOG.info('Authenticating API user: {0}, group={1}'.format(
            LENSE.REQUEST.USER.name,
            repr(LENSE.REQUEST.USER.group)
        ))
        handler_path = '{0}:{1}'.format(LENSE.REQUEST.method, LENSE.REQUEST.path)

        # Anonymous request
        if LENSE.REQUEST.is_anonymous:
            return LENSE.REQUEST.ensure(self.map['anon'],
                isnot = False,
                error = 'Request handler <{0}> does not support anonymous requests'.format(handler_path),
                log   = 'Processing anonymous request for <{0}>'.format(handler_path),
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

    def run(self):
        """
        Worker method for processing the incoming API request.
        """
        output   = ManifestInterface(LENSE.OBJECTS.HANDLER.get_manifest(handler=self.map['uuid'])).execute()

        # Construct a response object
        response = RequestOK(data=output['data'], message=output['message'])

        # Close any open SocketIO connections
        LENSE.SOCKET.disconnect()

        # OK
        return LENSE.HTTP.success(response.message, response.data)

    @classmethod
    def log_request(cls, response=None, code=200):
        """
        Class method for logging request data.

        :param response: The internal response object
        :type  response: object
        """

        # Log the request stats
        log_request_stats({
            'path': LENSE.REQUEST.path,
            'method': LENSE.REQUEST.method,
            'client_ip': LENSE.REQUEST.client,
            'client_user': LENSE.REQUEST.USER.name,
            'client_group': LENSE.REQUEST.USER.group,
            'endpoint': LENSE.REQUEST.host,
            'user_agent': LENSE.REQUEST.agent,
            'retcode': code,
            'req_size': int(LENSE.REQUEST.size),
            'rsp_size': int(getsizeof(getattr(response, 'data', ''))) + int(getsizeof(getattr(response, 'message', ''))),
            'rsp_time_ms': REQ_END - REQ_START
        })

    @classmethod
    def dispatch(cls, request):
        """
        Static method for dispatching the request object to the RequestManager.

        :param request: The incoming Django request object
        :type  request: HttpRequest
        """
        try:

            # Request timer start
            REQ_START = int(round(time() * 1000))

            # Setup Lense commons
            LENSE.SETUP.engine(request)

            # Run the request manager
            response = cls(request).run()

            # Request timer end
            REQ_END = int(round(time() * 1000))

            # Return the response
            return response

        # Internal request error
        except (EnsureError, RequestError, AuthError, ManifestError) as e:
            LENSE.LOG.exception(e.message)
            return LENSE.HTTP.error(e.message, e.code)
