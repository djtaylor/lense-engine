import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense import MODULE_ROOT
from lense.engine.api.handlers import RequestHandler
from lense.common.objects.acl.models import ACLObjects
from lense.common.objects.handler.models import Handlers
from lense.common.utils import valid, invalid, mod_has_class

class Handler_Delete(RequestHandler):
    """
    Delete an existing API handler.
    """
    def __init__(self, parent):
        self.api = parent

        # Target handler
        self.handler = self.api.data['uuid']

    def launch(self):
        """
        Worker method used for deleting a handler.
        """
        
        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=self.handler).count():
            return invalid(self.api.log.error('Could not delete handler [{0}], not found in database'.format(self.handler)))
        
        # Get the handler details
        handler_row = Handlers.objects.filter(uuid=self.handler).values()[0]
        
        # Make sure the handler isn't protected
        if handler_row['protected']:
            return invalid('Cannot delete a protected handler')
        
        # Delete the handler
        try:
            Handlers.objects.filter(uuid=self.handler).delete()
        except Exception as e:
            return invalid(self.api.log.exeption('Failed to delete handler: {0}'.format(str(e))))
        
        # Construct and return the web data
        web_data = {
            'uuid': self.handler
        }
        return valid('Successfully deleted handler', web_data)

class Handler_Create(RequestHandler):
    """
    Create a new API handler.
    """
    def __init__(self, parent):
        self.api  = parent

    def _get_rmap(self):
        if isinstance(self.api.data['rmap'], (dict, list)):
            return json.dumps(self.api.data['rmap'])
        return self.api.data['rmap']

    def launch(self):
        """
        Worker method for creating a new handler.
        """
        
        # Creation parameters
        params = {
            'uuid':       str(uuid4()),
            'name':       self.api.data['name'],
            'path':       self.api.data['path'],
            'desc':       self.api.data['desc'],
            'method':     self.api.data['method'],
            'mod':        self.api.data['mod'],
            'cls':        self.api.data['cls'],
            'utils':      json.dumps(self.api.data.get('utils', [])),
            'protected':  self.api.data['protected'],
            'enabled':    self.api.data['enabled'],
            'object':     self.api.data.get('object'),
            'object_key': self.api.data.get('object_key'),
            'allow_anon': self.api.data.get('allow_anon', False),
            'locked':     False,
            'locked_by':  None,
            'rmap':       self._get_rmap()
        }
        
        # Try to import the module and make sure it contains the class definition
        mod_status = mod_has_class(params['mod'], params['cls'])
        if not mod_status['valid']:
            return mod_status
        
        # Save the handler
        try:
            Handlers(**params).save()
            
            # Return the response
            return valid('Successfully created handler', {
                'uuid': params['uuid'],
                'path': params['path'],
                'method': params['method'],
                'desc': params['desc'],
                'enabled': params['enabled'],
                'protected': params['protected']
            })
            
        # Failed to save handler
        except Exception as e:
            return invalid('Failed to create handler: {0}'.format(str(e)))

class Handler_Save(RequestHandler):
    """
    Save changes to an API handler.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target handler
        self.handler = self.api.data['uuid']

    def launch(self):
        """
        Worker method for saving changes to a handler.
        """

        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=self.handler).count():
            return invalid(self.api.log.error('Could not save handler [{0}], not found in database'.format(self.handler)))

        # Validate the handler attributes
        #util_status = self.api.util.GatewayUtilitiesValidate.launch()
        #if not util_status['valid']:
        #    return util_status

        # Get the handler details
        util_row = Handlers.objects.filter(uuid=self.handler).values()[0]
    
        # Update parameters
        params = {
            'path': self.api.data.get('path', util_row['path']),
            'method': self.api.data.get('method', util_row['method']),
            'mod': self.api.data.get('mod', util_row['mod']),
            'cls': self.api.data.get('cls', util_row['cls']),
            'utils': self.api.data.get('utils', util_row['utils']),
            'rmap': self.api.data.get('rmap', util_row['rmap']),
            'enabled': self.api.data.get('enabled', util_row['enabled']),
            'protected': self.api.data.get('protected', util_row['protected']),
            'object': self.api.data.get('object', util_row['object']),
            'object_key': self.api.data.get('object_key', util_row['object_key']),
            'allow_anon': self.api.data.get('allow_anon', util_row['allow_anon'])
        }
    
        # Make sure utilities value is a string
        if isinstance(params['utils'], list):
            params['utils'] = json.dumps(params['utils'])
    
        # Make sure the request map value is a string'
        if isinstance(params['rmap'], dict):
            params['rmap'] = json.dumps(params['rmap'])

        # Attempt to update the handler
        try:
            Handlers.objects.filter(uuid=self.handler).update(**params)
            
        # Critical error when updating handler
        except Exception as e:
            return invalid(self.api.log.exception('Failed to update handler: {0}'.format(str(e))))

        # Successfully updated handler
        return valid('Successfully updated handler.')

class Handler_Validate(RequestHandler):
    """
    Validate changes to an API handler prior to saving.
    """
    def __init__(self, parent):
        self.api = parent

        # Target handler
        self.handler = self.api.data['uuid']

    def _validate(self):
        """
        Validate the handler attributes.
        """
    
        # Get all utilities
        util_all = Handlers.objects.all().values()
    
        # ACL objects
        acl_objects  = list(ACLObjects.objects.all().values())
    
        # Construct available external utilities
        util_ext = []
        for util in util_all:
            util_ext.append('%s.%s' % (util['mod'], util['cls']))
    
        # Get the handler details
        util_row = Handlers.objects.filter(uuid=self.handler).values()[0]
    
        # Default values
        default = {
            'path': self.api.data.get('path', util_row['path']),
            'method': self.api.data.get('method', util_row['method']),
            'mod': self.api.data.get('mod', util_row['mod']),
            'cls': self.api.data.get('cls', util_row['cls']),
            'utils': self.api.data.get('utils', util_row['utils']),
            'rmap': self.api.data.get('rmap', util_row['rmap']),
            'enabled': self.api.data.get('enabled', util_row['enabled']),
            'protected': self.api.data.get('protected', util_row['protected']),
            'object': self.api.data.get('object', util_row['object']),
            'object_key': self.api.data.get('object_key', util_row['object_key']),
            'allow_anon': self.api.data.get('allow_anon', util_row['allow_anon'])
        }
    
        # Make sure the path string is valid
        if not re.match(r'^[a-z0-9][a-z0-9\/]*[a-z0-9]$', default['path']):
            return invalid('Failed to validate handler [{0}], invalid [path] value: {1}'.format(self.handler, default['path']))
    
        # Make sure the method is valid
        if not default['method'] in ['GET', 'POST', 'PUT', 'DELETE']:
            return invalid('Failed to validate handler [{0}], invalid [method] value: {1}'.format(self.handler, default['method']))
    
        # Make sure the object type is supported
        obj_supported = False if default['object'] else True
        for acl_obj in acl_objects:
            if acl_obj['type'] == object:
                obj_supported = True
                break
        if not obj_supported:
            return invalid('Failed to validate handler, using unsupported handler object type [{0}]'.format(object))
    
        # Make sure the request map is valid JSON
        try:
            tmp = json.loads(rmap)
        except Exception as e:
            return invalid('Failed to validate request map JSON: {0}'.format(str(e)))
    
        # Validate the module
        mod_path = mod.replace('.', '/')
        if not os.path.isfile('{0}/{1}.py'.format(MODULE_ROOT, mod_path)):
            return invalid('Failed to validate handler [{0}], module [{1}] not found'.format(self.handler, mod))
    
        # Validate the class
        mod_status = mod_has_class(mod, cls)
        if not mod_status['valid']:
            return mod_status
    
        # Validate external utilities
        for util in utils:
            if not util in util_ext:
                return invalid('Failed to validate handler [{0}], could not locate external handler class [{1}]'.format(self.handler, util))
        
        # Utility validated
        return valid()

    def launch(self):
        """
        Worker method for validating handler changes.
        """
        
        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=self.handler).count():
            return invalid(self.api.log.error('Could not validate handler [{0}], not found in database'.format(self.handler)))

        # Validate the handler attributes
        util_status = self._validate()
        if not util_status['valid']:
            return util_status
        
        # Utility is valid
        return valid('Utility validation succeeded.')

class Handler_Close(RequestHandler):
    """
    Close an API handler and release the editing lock.
    """
    def __init__(self, parent):
        self.api = parent

        # Target handler
        self.handler = self.api.data['uuid']

    def launch(self):
        """
        Worker method for closing a handler and releasing the editing lock.
        """
    
        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=self.handler).count():
            return invalid(self.api.log.error('Could not check in handler [{0}], not found in database'.format(self.handler)))
        
        # Get the handler details row
        util_row = Handlers.objects.filter(uuid=self.handler).values()[0]
        
        # Check if the handler is already checked out
        if util_row['locked'] == False:
            return invalid(self.api.log.error('Could not check in handler [{0}], already checked in'.format(self.handler)))
        
        # Unlock the handler
        self.api.log.info('Checked in handler [{0}] by user [{1}]'.format(self.handler, self.api.user))
        try:
            Handlers.objects.filter(uuid=self.handler).update(
                locked    = False,
                locked_by = None
            )
            return valid('Successfully checked in handler')
            
        # Failed to check out the handler
        except Exception as e:
            return invalid(self.api.log.error('Failed to check in handler with error: {0}'.format(str(e))))

class Handler_Open(RequestHandler):
    """
    Open an API handler for editing.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target handler
        self.handler = self.api.data['uuid']
        
    def launch(self):
        """
        Worker method to open the handler for editing.
        """
        self.api.log.info('Preparing to checkout handler [{0}] for editing'.format(self.handler))
    
        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=self.handler).count():
            return invalid(self.api.log.error('Could not open handler [{0}] for editing, not found in database'.format(self.handler)))
        
        # Get the handler details row
        util_row = Handlers.objects.filter(uuid=self.handler).values()[0]
        
        # Check if the handler is locked
        if util_row['locked'] == True:
            self.api.log.info('Utility [{0}] already checked out by user [{1}]'.format(self.handler, util_row['locked_by']))
            
            # If the handler is checked out by the current user
            if util_row['locked_by'] == self.api.user:
                self.api.log.info('Utility checkout request OK, requestor [{0}] is the same as the locking user [{1}]'.format(self.api.user, util_row['locked_by']))
                return valid('Utility already checked out by the current user')
            else:
                return invalid(self.api.log.error('Could not open handler [{0}] for editing, already checked out by {1}'.format(self.handler, util_row['locked_by'])))
    
        # Set the locking user
        locked_by = self.api.user
        
        # Lock the handler for editing
        self.api.log.info('Checkout out handler [{0}] for editing by user [{1}]'.format(self.handler, locked_by))
        try:
            Handlers.objects.filter(uuid=self.handler).update(
                locked    = True,
                locked_by = self.api.user
            )
            return valid('Successfully checked out handler for editing')
            
        # Failed to check out the handler
        except Exception as e:
            return invalid(self.api.log.error('Failed to check out handler for editing with error: {0}'.format(str(e))))

class Handler_Get(RequestHandler):
    """
    Retrieve a listing of API utilities.
    """
    def __init__(self, parent):
        self.api = parent
        
    def launch(self):
        """
        Worker method to retrieve a listing of API utilities.
        """
        try:
            
            # If grabbing a specific handler
            if 'uuid' in self.api.data:
                
                # If the handler doesn't exist
                if not Handlers.objects.filter(uuid=self.api.data['uuid']).count():
                    return invalid('Utility [{0}] does not exist'.format(self.api.data['uuid']))
                return valid(json.dumps(Handlers.objects.filter(uuid=self.api.data['uuid']).values()[0]))
                
            # Return all utilities
            else:
                return valid(json.dumps(list(Handlers.objects.all().values())))
        except Exception as e:
            return invalid(self.api.log.exception('Failed to retrieve utilities listing: {0}'.format(str(e))))