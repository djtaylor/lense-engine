import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.exceptions import RequestError
from lense.engine.api.handlers import RequestHandler
from lense.common.objects.acl.models import ACLObjects
from lense.common.objects.handler.models import Handlers
from lense.common.utils import valid, invalid, mod_has_class

ERR_NO_UUID='No handler UUID found in request data'

class Handler_Delete(RequestHandler):
    """
    Delete an existing API handler.
    """
    def launch(self):
        """
        Worker method used for deleting a handler.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', None),
            value = str,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Look for the handler
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Make sure the handler isn't protected
        LENSE.REQUEST.ensure(handler.protected, 
            value = False, 
            error = 'Cannot delete a protected handler', 
            code  = 403)
        
        # Delete the handler
        LENSE.REQUEST.ensure(handler.delete, 
            call  = True, 
            value = True, 
            error = 'Failed to delete the handler: {0}'.format(target),
            code  = 500)
        
        # OK
        return valid('Successfully deleted handler', {'uuid': target})

class Handler_Create(RequestHandler):
    """
    Create a new API handler.
    """
    def launch(self):
        """
        Worker method for creating a new handler.
        """
        
        # Creation parameters
        params = {
            'uuid':       str(uuid4()),
            'name':       LENSE.REQUEST.data['name'],
            'path':       LENSE.REQUEST.data['path'],
            'desc':       LENSE.REQUEST.data['desc'],
            'method':     LENSE.REQUEST.data['method'],
            'mod':        LENSE.REQUEST.data['mod'],
            'cls':        LENSE.REQUEST.data['cls'],
            'protected':  LENSE.REQUEST.data['protected'],
            'enabled':    LENSE.REQUEST.data['enabled'],
            'object':     LENSE.REQUEST.data.get('object'),
            'object_key': LENSE.REQUEST.data.get('object_key'),
            'allow_anon': LENSE.REQUEST.data.get('allow_anon', False),
            'locked':     False,
            'locked_by':  None,
            'rmap':       json.dumps(LENSE.REQUEST.data['rmap'])
        }
        
        # Validate the handler object
        LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.check_object(params['mod'], params['cls']),
            value = True,
            error = 'Failed to validate handler object',
            code  = 400)
        
        # Save the handler
        LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.create(**params),
            value = True,
            error = 'Failed to create handler',
            code  = 500)
            
        # Return the response
        return valid('Successfully created handler', {
            'uuid': params['uuid'],
            'path': params['path'],
            'method': params['method'],
            'desc': params['desc'],
            'enabled': params['enabled'],
            'protected': params['protected']
        })

class Handler_Update(RequestHandler):
    """
    Update an existing API request handler.
    """
    def launch(self):
        """
        Worker method for saving changes to a handler.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', None),
            value = str,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Get the handler object
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
    
        # Update parameters
        params = {
            'path': LENSE.REQUEST.data.get('path', handler.path),
            'method': LENSE.REQUEST.data.get('method', handler.method),
            'mod': LENSE.REQUEST.data.get('mod', handler.mod),
            'cls': LENSE.REQUEST.data.get('cls', handler.cls),
            'rmap': LENSE.REQUEST.data.get('rmap', handler.rmap),
            'enabled': LENSE.REQUEST.data.get('enabled', handler.enabled),
            'protected': LENSE.REQUEST.data.get('protected', handler.protected),
            'object': LENSE.REQUEST.data.get('object', handler.object),
            'object_key': LENSE.REQUEST.data.get('object_key', handler.object_key),
            'allow_anon': LENSE.REQUEST.data.get('allow_anon', handler.allow_anon)
        }
    
        # Make sure the request map value is a string
        if isinstance(params['rmap'], dict):
            params['rmap'] = json.dumps(params['rmap'])

        # Attempt to update the handler
        LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.update(handler.uuid, params),
            value = True,
            error = 'Failed to update handler',
            code  = 500)

        # Successfully updated handler
        return valid('Successfully updated handler.')

class Handler_Validate(RequestHandler):
    """
    Validate changes to an API handler prior to saving.
    """
    def _validate(self):
        """
        Validate the handler attributes.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', None),
            value = str,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
    
        # ACL objects
        acl_objects = LENSE.OBJECTS.ACL.get_objects()
    
        # Get the handler details
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
    
        # Default values
        default = {
            'path': LENSE.REQUEST.data.get('path', handler.path),
            'method': LENSE.REQUEST.data.get('method', handler.method),
            'mod': LENSE.REQUEST.data.get('mod', handler.mod),
            'cls': LENSE.REQUEST.data.get('cls', handler.cls),
            'rmap': LENSE.REQUEST.data.get('rmap', handler.rmap),
            'enabled': LENSE.REQUEST.data.get('enabled', handler.enabled),
            'protected': LENSE.REQUEST.data.get('protected', handler.protected),
            'object': LENSE.REQUEST.data.get('object', handler.object),
            'object_key': LENSE.REQUEST.data.get('object_key', handler.object_key),
            'allow_anon': LENSE.REQUEST.data.get('allow_anon', handler.allow_anon)
        }
    
        # Make sure the path string is valid
        if not re.match(r'^[a-z0-9][a-z0-9\/]*[a-z0-9]$', default['path']):
            return invalid('Failed to validate handler [{0}], invalid [path] value: {1}'.format(target, default['path']))
    
        # Make sure the method is valid
        if not default['method'] in ['GET', 'POST', 'PUT', 'DELETE']:
            return invalid('Failed to validate handler [{0}], invalid [method] value: {1}'.format(target, default['method']))
    
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
            return invalid('Failed to validate handler [{0}], module [{1}] not found'.format(target, mod))
    
        # Validate the class
        mod_status = mod_has_class(mod, cls)
        if not mod_status['valid']:
            return mod_status
        
        # Utility validated
        return valid()

    def launch(self):
        """
        Worker method for validating handler changes.
        """
        
        # Make sure the handler exists
        if not Handlers.objects.filter(uuid=target).count():
            return invalid(LENSE.API.LOG.error('Could not validate handler [{0}], not found in database'.format(target)))

        # Validate the handler attributes
        handler = self._validate()
        if not handler['valid']:
            return handler
        
        # Utility is valid
        return valid('Utility validation succeeded.')

class Handler_Close(RequestHandler):
    """
    Close an API handler and release the editing lock.
    """
    def launch(self):
        """
        Worker method for closing a handler and releasing the editing lock.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', None),
            value = str,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
    
        # Make sure the handler exists
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Check if the handler is already checked out
        if handler.locked:
            return valid('Handler already checked in')
            
        # Update the lock attributes
        LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.update(target, {
            'locked': False,
            'locked_by': None
        }), error = 'Failed to check in handler {0}'.format(target),
            log   = 'Checking in hander {0}: locked=False'.format(target))
        
        # Handler checked in
        return valid('Handler checked in')
    
class Handler_Open(RequestHandler):
    """
    Open an API handler for editing.
    """ 
    def launch(self):
        """
        Worker method to open the handler for editing.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', None),
            value = str,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
    
        # Make sure the handler exists
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)

        # Check if the handler is locked
        if handler.locked == True:
            
            # If the handler is checked out by the current user
            if handler.locked_by == LENSE.REQUEST.USER.name:
                return valid('Utility already checked out by the current user')
            return invalid(LENSE.API.LOG.error('Could not open handler [{0}] for editing, already checked out by {1}'.format(target, handler['locked_by'])))
    
        # Set the locking user
        locked_by = LENSE.REQUEST.USER.name
        
        # Update the lock attributes
        LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.update(target, {
            'locked': True,
            'locked_by': locked_by
        }), error = 'Failed to check out handler {0}'.format(target),
            log   = 'Checking out hander {0}: locked=True'.format(target))
        
        # Handler checked in
        return valid('Handler checked out')
        
class Handler_Get(RequestHandler):
    """
    Retrieve a listing of API utilities.
    """
    def __init__(self):
        target = LENSE.REQUEST.data.get('uuid', None)
    
    def launch(self):
        """
        Worker method to retrieve a listing of API utilities.
        """
        if not target:
            return valid(json.dumps(LENSE.OBJECTS.HANDLER.get()))
        
        # Make sure the handler exists
        handler = LENSE.REQUEST.ensure(LENSE.OBJECTS.HANDLER.get(uuid=target), 
            value = object, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the handler
        return valid(json.dumps(LENSE.OBJECTS.HANDLER.get(uuid=target)))