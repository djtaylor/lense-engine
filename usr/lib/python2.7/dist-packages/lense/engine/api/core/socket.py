import json
from socketIO_client import SocketIO

class SocketResponse(object):
    """
    SocketResponse
    
    Class responsible for handling responses sent to the Socket.IO proxy server. This is used to
    send messages back to web clients that used the JavaScript Socket.IO client to make API requests.
    Clients are distinguished by a unique string, consisting of their API username and session ID.
    """
    def __init__(self):
        
        # SocketIO client / web socket parameters
        self.socket_io  = None
        self.web_socket = None
        
    def construct(self):
        """
        Construct the Socket.IO client for sending responses.
        """
        try:
            
            # If the Socket.IO proxy server is enabled
            if LENSE.CONF.socket.enable:
                
                LENSE.LOG.info('Opening SocketIO proxy connection: {}:{}'.format(LENSE.CONF.socket.host, LENSE.CONF.socket.port))
            
                # Open the Socket.IO client connection
                self.socket_io = SocketIO(LENSE.CONF.socket.host, int(LENSE.CONF.socket.port))
                
                # Socket connection opened sucessfully
                LENSE.LOG.info('Initialized SocketIO proxy connection')
                
            else:
                LENSE.LOG.info('SocketIO proxy server disabled - skipping...')
            
        # Critical error when opening connection
        except Exception as e:
            LENSE.LOG.info('Failed to initialize SocketIO proxy connection: {}'.format(str(e)))
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
            LENSE.LOG.info('Closing SocketIO proxy connection')
        except:
            pass
        
    def broadcast(self, t, d={}):
        """
        Broadcast data to all web socket clients.
        """
        if self.socket_io and LENSE.CONF.socket.enable:
            self.socket_io.emit('update', {'type': t, 'content': d})
        
    def loading(self, m=None):
        """
        Send a loading messages to a web socket client.
        """
        if self.web_socket and self.socket_io and LENSE.CONF.socket.enable:
            self.socket_io.emit('update', { 'room': self.web_socket['room'], 'type': 'loading', 'content': m})