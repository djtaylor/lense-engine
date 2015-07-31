import json
from socketIO_client import SocketIO

# Lense Libraries
from lense.common import config
from lense.common import logger

class SocketResponse(object):
    """
    SocketResponse
    
    Class responsible for handling responses sent to the Socket.IO proxy server. This is used to
    send messages back to web clients that used the JavaScript Socket.IO client to make API requests.
    Clients are distinguished by a unique string, consisting of their API username and session ID.
    """
    def __init__(self):
        
        # Configuration / logger
        self.conf       = config.parse('SERVER')
        self.log        = logger.create(__name__, self.conf.server.log)
        
        # SocketIO client / web socket parameters
        self.socket_io  = None
        self.web_socket = None
        
    def construct(self):
        """
        Construct the Socket.IO client for sending responses.
        """
        try:
            
            # If the Socket.IO proxy server is enabled
            if self.conf.socket.enable:
                
                self.log.info('Opening SocketIO proxy connection: {}:{}'.format(self.conf.socket.host, self.conf.socket.port))
            
                # Open the Socket.IO client connection
                self.socket_io = SocketIO(self.conf.socket.host, int(self.conf.socket.port))
                
                # Socket connection opened sucessfully
                self.log.info('Initialized SocketIO proxy connection')
                
            else:
                self.log.info('SocketIO proxy server disabled - skipping...')
            
        # Critical error when opening connection
        except Exception as e:
            self.log.info('Failed to initialize SocketIO proxy connection: {}'.format(str(e)))
            return False
        
        # Return the constructed Socket.IO client
        return self
        
    def set(self, web_socket):
        """
        Set the web socket client attributes.
        """
        self.web_socket = web_socket
        
        # Return the web socket attributes
        return web_socket
        
    def disconnect(self):
        """
        Disconnect the Socket.IO client.
        """
        try:
            self.socket_io.disconnect()
            self.log.info('Closing SocketIO proxy connection')
        except:
            pass
        
    def broadcast(self, t, d={}):
        """
        Broadcast data to all web socket clients.
        """
        if self.socket_io and self.conf.socket.enable:
            self.socket_io.emit('update', {'type': t, 'content': d})
        
    def loading(self, m=None):
        """
        Send a loading messages to a web socket client.
        """
        if self.web_socket and self.socket_io and self.conf.socket.enable:
            self.socket_io.emit('update', { 'room': self.web_socket['room'], 'type': 'loading', 'content': m})