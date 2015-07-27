import re
import copy
import json
import importlib

# Django Libraries
from django.http import HttpResponse
from django.core.mail import send_mail
from django.test.client import RequestFactory
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense.common import config
from lense.common import logger
from lense.common.http import PATH, MIME_TYPE, JSONError, JSONException
from lense.common.utils import valid, invalid
from lense.common.collection import Collection
from lense.engine.api.objects.cache import CacheManager
from lense.engine.api.objects.manager import ObjectsManager
from lense.engine.api.core.socket import SocketResponse

class APIEmail(object):
    """
    Wrapper class for handling emails.
    """
    def __init__(self):
        self.conf = config.parse('SERVER')
        self.log  = logger.create(__name__, self.conf.server.log)
    
    def send(self, subject, body, sender, recipient):
        """
        Send an email.
        
        @param subject:   The subject of the email
        @type  subject:   str
        @param body:      The body of the email
        @type  body:      str
        @param sender:    The sender's email
        @type  sender:    str
        @param recipient: Email recipients
        @type  list|str   A list of recipient emails, or a single email string
        """
        if self.conf.email.smtp_enable:
                
            # Send the email
            try:
                
                # Supports a single or list of recipients
                _recipient = recipient if isinstance(recipient, list) else [recipient]
                
                # Send the email
                send_mail(subject, body, from_email=sender, recipient_list=_recipient, fail_silently=False)
                self.log.info('Sent email to "{}"'.format(_recipient))
                return True
            
            # Failed to send email
            except Exception as e:
                self.log.exception('Failed to send email to "{}": {}'.format(str(_recipient), str(e)))
                return False

        # SMTP disabled
        else:
            return False

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
        
        # Configuration / logger
        self.conf    = config.parse('SERVER')
        self.log     = APILogger(self)
        self.log_int = logger.create(path, self.conf.server.log)
        
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
        
        # Configuration / internal logger
        self.conf         = config.parse('SERVER')
        self.log_int      = logger.create('{}:{}'.format(self.path, self.method), self.conf.server.log)

        # External utilities / utilities object / cache manager / objects manager / ACL gateway
        self.utils        = utils
        self.util         = None
        self.cache        = CacheManager()
        self.objects      = ObjectsManager()
        self.acl          = acl

        # SocketIO client / web socket object
        self.socket       = SocketResponse().construct()
        self.websock      = None
     
    def _utils(self):
        """
        Construct the external utilities object. Scan each item in the utilities list retrieved
        from the utility database entry, and attempt to create an instance of the module/class.
        """
        if self.utils and isinstance(self.utils, list):
            util_obj = {}
            for util in self.utils:
                mod_name   = re.compile('(^.*)\.[^\.]*$').sub(r'\g<1>', util)
                class_name = re.compile('^.*\.([^\.]*$)').sub(r'\g<1>', util)
                
                # Import each enabled utility class
                mod_obj    = importlib.import_module(mod_name)
                class_obj  = getattr(mod_obj, class_name)
                class_inst = class_obj(copy.copy(self))
                self.log_int.info('Loading utility class: [{}]'.format(class_inst))
                
                # Add to the utilities object
                util_obj[class_name] = class_inst
                
            # Store the utility instance
            self.util = Collection(util_obj).get()
        
    def _set_websock(self):
        """
        Check if the client is making a request via the Socket.IO proxy server.
        """
        if 'socket' in self.request.data:
            
            # Log the socket connection
            self.log_int.info('Received connection from web socket client: {}'.format(str(self.request.data['socket'])))
            
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
        
        # Import the utility classes
        self._utils()
        
        # Set the logger object
        self.log = APILogger(self)
        
        # Return the constructed API object, ready for authentication or other requests
        return valid(self)
    
class APILogger(object):
    """
    APILogger
    
    Common logger class used to handle logging messages and returning HTTP responses.
    """
    def __init__(self, parent, client=None):
        """
        Initialize APILogger

        @param parent: Parent class attributes
        @type  parent: class
        @param client: The client IP address
        @type  client: str
        """
        self.api     = parent

        # Container for the current log message
        self.log_msg = None

        # Default parameters
        if hasattr(self.api.request, 'client') and not client:
            self.client = self.api.request.client
        else:
            self.client = 'localhost' if not client else client

    def _websock_response(self, status, _data={}):
        """
        Construct and return a JSON web socket response for the Socket.IO proxy server.
        
        @param status: Boolean string
        @type  status: str
        @param data:   Any response data in addition to the body message
        @type  data:   dict
        """
        return json.dumps({
            'room':     self.parent.websock['room'],
            'msg':      self.log_msg,
            'path':     self.parent.path,
            'callback': False if not ('callback' in self.parent.websock) else self.parent.websock['callback'],
            'status':   status,
            '_data':    _data
        }, cls=DjangoJSONEncoder)

    def _api_response(self, ok=False, data={}):
        """
        Construct the API response body to send back to clients. Constructs the websocket data
        to be interpreted by the Socket.IO proxy server if relaying back to a web client.
        
        @param ok:   Has the request been successfull or not
        @type  ok:   bool
        @param data: Any data to return in the SocketIO response
        @type  data: dict
        """
        
        # Status flag
        status = 'true' if ok else 'false'
        
        # Web socket responses
        if self.api.websock:
            return self._websock_response(status, data)
            
        # Any paths that don't supply web socket responses    
        else:
            
            # Return a JSON encoded object if a dictionary or list
            if isinstance(self.log_msg, dict) or isinstance(self.log_msg, list):
                return json.dumps(self.log_msg, cls=DjangoJSONEncoder)
            
            # Otherwise return a string
            return self.log_msg

    def info(self, log_msg):
        """
        Handle the logging of information messages.
        
        @param log_msg:  The message to log/return to the client
        @type  log_msg:  str
        """
        self.log_msg = log_msg
        self.api.log_int.info('client({}): {}'.format(self.client, log_msg))
        return log_msg
        
    def debug(self, log_msg):
        """
        Handle the logging of debug messages.
        
        @param log_msg:  The message to log/return to the client
        @type  log_msg:  str
        """
        self.api.log_int.info('client({}): {}'.format(self.client, log_msg))
        return log_msg
        
    def success(self, log_msg, web_data={}):
        """
        Handle the logging of success messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param log_msg:  The message to log/return to the client
        @type  log_msg:  str
        @param web_data: Any additional data to return to a web client via SocketIO
        @type  web_data: dict
        """
        def _set_log_msg(log_msg):
            if not isinstance(log_msg, list) and not isinstance(log_msg, dict):
                return 'API request was successfull' if not log_msg else log_msg
            else:
                return log_msg

        # Default log message if not specified
        self.log_msg = _set_log_msg(log_msg)
            
        # Log the success message
        self.api.log_int.info('client({}): {}'.format(self.client, log_msg))
        
        # Return the HTTP response
        return HttpResponse(self._api_response(True, web_data), MIME_TYPE.APPLICATION.JSON, status=200)
    
    def exception(self, log_msg=None, code=None, web_data={}):
        """
        Handle the logging of exception messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param log_msg:  The message to log/return to the client
        @type  log_msg:  str
        @param code:     The HTTP status code
        @type  code:     int
        @param web_data: Any additional data to return to a web client via SocketIO
        @type  web_data: dict
        """
        
        # Default log message if not specified
        self.log_msg = 'An exception occured when processing your API request' if not log_msg else log_msg
    
        # Log the exception
        self.api.log_int.exception('client({}): {}'.format(self.client, self.log_msg))
    
        # If returning a response to a client
        if code and isinstance(code, int):
        
            # Return an error response
            return JSONException(error=self._api_response(False, web_data)).response()
        
        # Return the message string if internal
        return self.log_msg
    
    def error(self, log_msg=None, code=None, web_data={}):
        """
        Handle the logging of error messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param log_msg:  The message to log/return to the client
        @type  log_msg:  str
        @param code:     The HTTP status code
        @type  code:     int
        @param web_data: Any additional data to return to a web client via SocketIO
        @type  web_data: dict
        """
        
        # Default log message if not specified
        self.log_msg = 'An unknown error occured when processing your API request' if not log_msg else log_msg
        
        # Log the error message
        self.api.log_int.error('client({}): {}'.format(self.client, self.log_msg))
        
        # If returning a resposne to a client
        if code and isinstance(code, int):
        
            # Return an error response
            return JSONError(error=self._api_response(False, web_data), status=code).response()
        
        # Return the message string if internal
        return self.log_msg