from lense.common.utils import valid
from lense.engine.api.core.mailer import APIEmail
from lense.engine.api.core.logger import APILogger
from lense.engine.api.core.socket import SocketResponse

class APIBase(object):
    """
    APIBase
    
    Base class in the inheritance model used by all API utilties assigned to a path, and a
    handful of other class definitions. This class contains common attributes used by all API
    utilities, such as the logger, path details, external utilities, request attributes, etc.
    """
    def __init__(self, acl=None):
        """
        Initialize the APIBase class.
        
        :param acl: The ACL gateway generated during request initialization
        :type  acl: ACLGateway
        """
        LENSE.connect_socket()
        
        # Email / request handler / ACL gateway / websocket object
        self.email        = APIEmail()
        self.handler      = None
        self.acl          = acl
        
    def _set_websock(self):
        """
        Check if the client is making a request via the Socket.IO proxy server.
        """
        if 'socket' in LENSE.REQUEST.data:
            LENSE.LOG.info('Received connection from web socket client: {}'.format(str(LENSE.REQUEST.data['socket'])))
            
            # Set the web socket response attributes
            LENSE.SOCKET.set(LENSE.REQUEST.data['socket'])
        
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