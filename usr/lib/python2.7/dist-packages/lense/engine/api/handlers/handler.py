import json

# Lense Libraries
from lense.common.http import HTTP_METHODS
from lense.engine.api.handlers import RequestHandler

ERR_NO_UUID='No handler UUID found in request data'

class Handler_Delete(RequestHandler):
    """
    Delete an existing API handler.
    """
    def launch(self):
        """
        Worker method used for deleting a handler.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
        
        # Look for the handler
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = None, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Make sure the handler isn't protected
        self.ensure(handler.protected, 
            value = False, 
            error = 'Cannot delete a protected handler', 
            code  = 403)
        
        # Delete the handler
        self.ensure(handler.delete(),
            error = 'Failed to delete the handler: {0}'.format(target),
            log   = 'Deleted handler {0}'.format(target),
            code  = 500)
        
        # OK
        return self.ok('Successfully deleted handler', {'uuid': target})

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
            'uuid':       self.create_uuid(),
            'name':       self.get_data('name'),
            'path':       self.get_data('path'),
            'desc':       self.get_data('desc'),
            'method':     self.get_data('method'),
            'mod':        self.get_data('mod'),
            'cls':        self.get_data('cls'),
            'protected':  self.get_data('protected'),
            'enabled':    self.get_data('enabled'),
            'object':     self.get_data('object'),
            'object_key': self.get_data('object_key'),
            'allow_anon': self.get_data('allow_anon', False),
            'locked':     False,
            'locked_by':  None,
            'rmap':       json.dumps(self.get_data('rmap'))
        }
        
        # Validate the handler object
        self.ensure(LENSE.OBJECTS.HANDLER.check_object(params['mod'], params['cls']),
            error = 'Failed to validate handler object',
            code  = 400)
        
        # Handler attributes string
        attrs_str = 'uuid={0}, name={1}, path={2}, method={3}'.format(params['uuid'], params['name'], params['path'], params['method'])
        
        # Save the handler
        self.ensure(LENSE.OBJECTS.HANDLER.create(**params),
            isnot = False,
            error = 'Failed to create handler: {0}'.format(attrs_str),
            log   = 'Created handler: {0}'.format(attrs_str),
            code  = 500)
            
        # OK
        return self.ok('Successfully created handler', {
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
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
        
        # Get the handler object
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = None, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
    
        # Update parameters
        params = {
            'path': self.get_data('path', handler.path),
            'method': self.get_data('method', handler.method),
            'mod': self.get_data('mod', handler.mod),
            'cls': self.get_data('cls', handler.cls),
            'rmap': self.get_data('rmap', handler.rmap),
            'enabled': self.get_data('enabled', handler.enabled),
            'protected': self.get_data('protected', handler.protected),
            'object': self.get_data('object', handler.object),
            'object_key': self.get_data('object_key', handler.object_key),
            'allow_anon': self.get_data('allow_anon', handler.allow_anon)
        }
    
        # Make sure the request map value is a string
        if isinstance(params['rmap'], dict):
            params['rmap'] = json.dumps(params['rmap'])

        # Handler attributes string
        attrs_str = 'uuid={0}, name={1}, path={2}, method={3}'.format(handler.uuid, params['name'], params['path'], params['method'])

        # Attempt to update the handler
        self.ensure(LENSE.OBJECTS.HANDLER.update(handler.uuid, params),
            log   = 'Updated handler: {0}'.format(attrs_str),
            error = 'Failed to update handler: {0}'.format(attrs_str),
            code  = 500)

        # Successfully updated handler
        return self.ok(message='Successfully updated handler.')

class Handler_Validate(RequestHandler):
    """
    Validate changes to an API handler prior to saving.
    """
    def _validate(self, handler):
        """
        Validate the handler attributes.
        """
    
        # Default values
        default = {
            'path': self.get_data('path', handler.path),
            'method': self.get_data('method', handler.method),
            'mod': self.get_data('mod', handler.mod),
            'cls': self.get_data('cls', handler.cls),
            'rmap': self.get_data('rmap', handler.rmap),
            'enabled': self.get_data('enabled', handler.enabled),
            'protected': self.get_data('protected', handler.protected),
            'object': self.get_data('object', handler.object),
            'object_key': self.get_data('object_key', handler.object_key),
            'allow_anon': self.get_data('allow_anon', handler.allow_anon)
        }
    
        # Make sure the path string is valid
        self.ensure(self.match(r'^[a-z0-9][a-z0-9\/]*[a-z0-9]$', default['path']),
            error = 'Failed to validate handler {0}, invalid "path" value: {1}'.format(handler.uuid, default['path']),
            debug = 'Handler {0} path {1} OK'.format(handler.uuid, default['path']),
            code  = 400)
    
        # Make sure the method is valid
        self.ensure(self.in_list(default['method'], HTTP_METHODS),
            error = 'Failed to validate handler {0}, invalid "method" value: {1}'.format(handler.uuid, default['method']),
            debug = 'Handler {0} method {1} OK'.format(handler.uuid, default['method']),
            code  = 400)
    
        # Make sure the object type is supported
        self.ensure(self.acl_object_supported(default.get('object', None)),
            error = 'Failed to validate handler {0}, unsupported object type: {1}'.format(handler.uuid, default['object']),
            code  = 400)
    
        # Make sure the request map is valid JSON
        self.ensure(json.loads,
            isnot = None,
            error = 'Failed to validate handler {0} request map'.format(handler.uuid),
            code  = 400,
            call  = True,
            args  = [default['rmap']])
    
        # Validate the module
        self.ensure(self.is_module(default['mod']),
            error = 'Failed to validate handler {0}, module {1} not found'.format(handler.uuid, default['mod']),
            code  = 400)
    
        # Validate the class
        self.ensure(self.mod_has_class(default['mod'], default['cls']),
            error = 'Failed to validate handler {0}, class {1} not found in {2}'.format(handler.uuid, default['cls'], default['mod']),
            code  = 400)
        
        # Handler validated
        return True

    def launch(self):
        """
        Worker method for validating handler changes.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
        
        # Make sure the handler exists
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = None, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)

        # Validate the handler attributes
        self._validate(handler)
        
        # Utility is valid
        return self.ok(message='Handler validation succeeded.')

class Handler_Close(RequestHandler):
    """
    Close an API handler and release the editing lock.
    """
    def launch(self):
        """
        Worker method for closing a handler and releasing the editing lock.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
    
        # Make sure the handler exists
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = None, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Check if the handler is already checked out
        if handler.locked:
            return self.valid('Handler already checked in')
            
        # Update the lock attributes
        self.ensure(LENSE.OBJECTS.HANDLER.update(target, {
            'locked': False,
            'locked_by': None
        }), error = 'Failed to check in handler {0}'.format(target),
            log   = 'Checking in hander {0}: locked=False'.format(target))
        
        # Handler checked in
        return self.ok(message='Handler checked in')
    
class Handler_Open(RequestHandler):
    """
    Open an API handler for editing.
    """ 
    def launch(self):
        """
        Worker method to open the handler for editing.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
    
        # Make sure the handler exists
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = False, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)

        # Check if the handler is locked
        if handler.locked == True:
            self.ensure(handler.locked_by,
                value = LENSE.REQUEST.USER.name,
                error = 'Could not open handler {0}, already checked out by {1}'.format(handler.uuid, handler.locked_by),
                code  = 400)
            return self.valid('Handler already checked out by current user')
        
        # Update the lock attributes
        self.ensure(LENSE.OBJECTS.HANDLER.update(target, {
            'locked': True,
            'locked_by': LENSE.REQUEST.USER.name
        }), error = 'Failed to check out handler {0}'.format(target),
            log   = 'Checking out hander {0}: locked=True'.format(target))
        
        # Handler checked in
        return self.ok(message='Handler checked out')
        
class Handler_Get(RequestHandler):
    """
    Retrieve a listing of API utilities.
    """
    def launch(self):
        """
        Worker method to retrieve a listing of API utilities.
        """
        target = self.get_data('uuid', None)
        
        # Return all handlers
        if not target:
            return LENSE.OBJECTS.HANDLER.get()
        
        # Look for the handler
        handler = self.ensure(LENSE.OBJECTS.HANDLER.acl().get(uuid=target), 
            isnot = None, 
            error = 'Could not find handler: {0}'.format(target),
            debug = 'Handler {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the handler details
        return self.ok(data=handler.values())