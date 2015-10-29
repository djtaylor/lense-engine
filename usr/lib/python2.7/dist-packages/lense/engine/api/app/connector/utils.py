import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense.common.http import HTTP_GET
from lense.common.utils import valid, invalid, set_response
from lense.engine.api.app.connector.models import DBConnectors, DBConnectorsOAuth2

class ConnectorsGet:
    """
    Retrieve existing API connectors.
    """
    def __init__(self, parent):
        self.api = parent

        # Target connector
        self.connector = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method for retrieving a connector.
        """
        
        # Construct a list of authorized connector objects
        auth_connectors = self.api.acl.authorized_objects('connector', path='connector', method=HTTP_GET)
        
        # If retrieving a specific user
        if self.connector:
            
            # If the connector does not exist or access is denied
            if not self.connector in auth_connectors.ids:
                return invalid('Connector "{0}" does not exist or access denied'.format(self.connector))
            
            # Return the connector details
            return valid(auth_connectors.extract(self.connector))
            
        # If retrieving all connectors
        else:
            return valid(set_response(auth_connectors.details, '[]'))

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
        
        # Creation parameters
        params = {
            'uuid':       str(uuid4()),
            'name':       self.api.data['name'],
            'is_oauth2':  self.api.data.get('is_oauth2', False)
        }
        
        # Make sure the connector doesn't exist
        if DBConnectors.objects.filter(name=params['name']).count():
            return invalid('Connector "{0}" already exists'.format(params['name']))
        
        # If setting up an OAuth2 API connector
        if params['is_oauth2']:
            for k in ['key_file', 'token_url', 'auth_url']:
                if not k in self.api.data:
                    return invalid('Missing required key "{0}" for OAuth2 API connector'.format(k))
        
        # Save the connector
        try:
            connector = DBConnectors(**params)
            connector.save()
            
            # If creating an OAuth2 connector
            if params['is_oauth2']:
                oauth2_params = {
                    'uuid': str(uuid4()),
                    'connector': connector,
                    'key_file': self.api.data['key_file'],
                    'token_url': self.api.data['token_url'],
                    'auth_url': self.api.data['auth_url']
                }
                
                # Create the OAuth2 entry
                DBConnectorsOAuth2(**oauth2_params).save()
            
            # Return the response
            return valid('Successfully created connector', {
                'uuid': params['uuid'],
                'name': params['name']
            })
            
        # Failed to save utility
        except Exception as e:
            return invalid('Failed to create connector: {0}'.format(str(e)))

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
        self.connector = self.api.acl.target_object()

    def launch(self):
        """
        Worker method for deleting a connector.
        """
        
        # Construct a list of authorized connector objects
        auth_connectors = self.api.acl.authorized_objects('connector', path='connector', method=HTTP_GET)
        
        # If the connector does not exist or access is denied
        if not self.connector in auth_connectors.ids:
            return invalid('Cannot delete connector "{0}", not found or access denied'.format(self.connector))
        self.api.log.info('Deleting API connector "{0}"'.format(self.connector))

        # Delete the API connector
        DBConnectors.objects.filter(uuid=self.connector).delete()
        
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