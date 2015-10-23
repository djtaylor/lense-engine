import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense.common.utils import valid, invalid
from lense.engine.api.app.connector.models import DBConnectors

class ConnectorsGet:
    """
    Retrieve existing API connectors.
    """
    def __init__(self, parent):
        self.api = parent

        # Target connector
        self.connector = self.api.data['uuid']
        
    def launch(self):
        """
        Worker method for retrieving a connector.
        """
        
        # Construct and return the web data
        return valid('Successfully retrieved connector', {})

class ConnectorsCreate:
    """
    Create a new API connector.
    """
    def __init__(self, parent):
        self.api = parent

    def launch(self):
        """
        Worker method for creating a connector.
        """
        
        # Construct and return the web data
        return valid('Successfully created connector', {})

class ConnectorsUpdate:
    """
    Update an existing API connector.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target connector
        self.connector = self.api.data['uuid']

    def launch(self):
        """
        Worker method for updating a connector.
        """
        
        # Construct and return the web data
        return valid('Successfully updated connector', {})

class ConnectorsDelete:
    """
    Delete an existing API connector.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target connector
        self.connector = self.api.data['uuid']

    def launch(self):
        """
        Worker method for deleting a connector.
        """
        
        # Construct and return the web data
        return valid('Successfully deleted connector', {})
    
class ConnectorCallback:
    """
    Handle connector callback URLs.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target callback
        self.callback = self.api.data['uuid']

    def launch(self):
        """
        Worker method for handling a connector callback.
        """
        
        # Construct and return the web data
        return valid('Successfully processed callback', {})