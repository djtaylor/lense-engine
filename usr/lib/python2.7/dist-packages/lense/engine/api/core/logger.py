import json

# Django Libraries
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense.common.http import PATH, MIME_TYPE, JSONError, JSONException

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
        self.msg = None

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
            'msg':      self.msg,
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
            if isinstance(self.msg, dict) or isinstance(self.msg, list):
                return json.dumps(self.msg, cls=DjangoJSONEncoder)
            
            # Otherwise return a string
            return self.msg

    def info(self, msg):
        """
        Handle the logging of information messages.
        
        @param msg:  The message to log/return to the client
        @type  msg:  str
        """
        self.msg = msg
        LENSE.LOG.info('client({0}): {1}'.format(self.client, msg))
        return msg
        
    def debug(self, msg):
        """
        Handle the logging of debug messages.
        
        @param msg:  The message to log/return to the client
        @type  msg:  str
        """
        LENSE.LOG.debug('client({0}): {1}'.format(self.client, msg))
        return msg
        
    def success(self, msg, data={}):
        """
        Handle the logging of success messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param msg:  The message to log/return to the client
        @type  msg:  str
        @param data: Any additional data to return to a web client via SocketIO
        @type  data: dict
        """
        def _set_msg(msg):
            if not isinstance(msg, list) and not isinstance(msg, dict):
                return 'API request was successfull' if not msg else msg
            return msg
        self.msg = _set_msg(msg)
            
        # Log the success message
        LENSE.LOG.info('client({}): {}'.format(self.client, msg))
        
        # Return the HTTP response
        return HttpResponse(self._api_response(True, data), MIME_TYPE.APPLICATION.JSON, status=200)
    
    def exception(self, msg=None, code=None, data={}):
        """
        Handle the logging of exception messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param msg:  The message to log/return to the client
        @type  msg:  str
        @param code: The HTTP status code
        @type  code: int
        @param data: Any additional data to return to a web client via SocketIO
        @type  data: dict
        """
        self.msg = 'An exception occured when processing your API request' if not msg else msg
        LENSE.LOG.exception('client({}): {}'.format(self.client, self.msg))
    
        # If returning a response to a client
        if code and isinstance(code, int):
            return JSONException(error=self._api_response(False, data)).response()
        return self.msg
    
    def error(self, msg=None, code=None, data={}):
        """
        Handle the logging of error messages. Returns an HTTP response object that can be
        sent by the API request handler back to the client.
        
        @param msg:  The message to log/return to the client
        @type  msg:  str
        @param code: The HTTP status code
        @type  code: int
        @param data: Any additional data to return to a web client via SocketIO
        @type  data: dict
        """
        self.msg = 'An unknown error occured when processing your API request' if not msg else msg
        LENSE.LOG.error('client({}): {}'.format(self.client, self.msg))
        
        # If returning a response to a client
        if code and isinstance(code, int):
            return JSONError(error=self._api_response(False, data), status=code).response()
        return self.msg