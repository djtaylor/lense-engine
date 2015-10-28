import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense.common.http import HTTP_GET
from lense.common.utils import valid, invalid
from lense.engine.api.app.integrator.models import DBIntegrators
from lense.engine.api.app.gateway.models import DBUtilities

class IntegratorsGet:
    """
    Retrieve existing API integrators.
    """
    def __init__(self, parent):
        self.api = parent

        # Target integrator
        self.connector = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method for retrieving an integrator.
        """
        
        # Construct a list of authorized integrator objects
        auth_integrators = self.api.acl.authorized_objects('integrator', path='integrator', method=HTTP_GET)
        
        # If retrieving a specific integrator
        if self.connector:
            
            # If the integrator does not exist or access is denied
            if not self.integrator in auth_integrators.ids:
                return invalid('Integrator "{0}" does not exist or access denied'.format(self.integrator))
            
            # Return the integrator details
            return valid(auth_integrators.extract(self.integrator))
            
        # If retrieving all integrators
        else:
            return valid(auth_integrators.details)

class IngtegratorsCreate:
    """
    Create a new API integrator.
    """
    def __init__(self, parent):
        self.api = parent

    def _path_conflict(self, path, method):
        """
        Look for any path conflicts.
        """

        # Get a list of existing utility paths
        util_paths = [x['path'] for x in DBUtilities.objects.values()]

        # If the path conflicts with a utility
        if path in util_paths:
            return invalid('Cannot create an integrator with the same path as a utility')

        # Get a list of existing integrators
        for i in DBIntegrators.objects.values():
            if (i['path'] == path) and (i['method'] == method):
                return invalid('Integrator conflicts with "{0}": path={1}, method={2}'.format(i['uuid'], i['path'], i['method']))

        # No path conflict
        return valid()

    def launch(self):
        """
        Worker method for creating an integrator.
        """
        
        # Creation parameters
        params = {
            'uuid':       str(uuid4()),
            'name':       self.api.data['name'],
            'path':       self.api.data['path'],
            'method':     self.api.data['method'],
            'imap':       self.api.data['imap']
        }
        
        # Make sure the integrator doesn't exist
        if DBIntegrators.objects.filter(name=params['name']).count():
            return invalid('Integrator "{0}" already exists'.format(params['name']))
        
        # Look for a path conflict
        path_check = self._path_conflict(params['path'], params['method'])
        if not path_check['valid']:
            return path_check
        
        # Save the integrator
        try:
            integrator = DBIntegrators(**params)
            integrator.save()
            
            # Return the response
            return valid('Successfully created integrator', params)
            
        # Failed to save integrator
        except Exception as e:
            return invalid('Failed to create integrator: {0}'.format(str(e)))

class IntegratorsUpdate:
    """
    Update an existing API integrator.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target integrator
        self.integrator = self.api.data['uuid']

    def launch(self):
        """
        Worker method for updating an integrator.
        """
        
        # Construct and return the web data
        return valid('Successfully updated integrator', {})

class IntegratorsDelete:
    """
    Delete an existing API integrator.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target integrator
        self.integrator = self.api.acl.target_object()

    def launch(self):
        """
        Worker method for deleting an integrator.
        """
        
        # Construct a list of authorized integrator objects
        auth_integrators = self.api.acl.authorized_objects('integrator', path='integrator', method=HTTP_GET)
        
        # If the integrator does not exist or access is denied
        if not self.integrator in auth_integrators.ids:
            return invalid('Cannot delete integrator "{0}", not found or access denied'.format(self.integrator))
        self.api.log.info('Deleting API integrator "{0}"'.format(self.integrator))

        # Delete the API integrator
        DBIntegrators.objects.filter(uuid=self.integrator).delete()
        
        # Construct and return the web data
        return valid('Successfully deleted integrator', {})