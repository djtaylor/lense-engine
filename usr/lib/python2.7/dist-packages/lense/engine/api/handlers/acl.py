from lense.engine.api.handlers import RequestHandler
from lense.common.objects.acl.models import ACLKeys, ACLObjects, ACLGlobalAccess, ACLObjectAccess

ERR_NO_UUID='No ACL object UUID found in request data'

class ACLObjects_Delete(RequestHandler):
    """
    Delete an existing ACL object definition.
    """
    def launch(self):
        """
        Worker method for deleting an ACL object definition.
        """
        target = self.ensure(self.get_data('uuid', False),
            error = ERR_NO_UUID,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')),
            code  = 400)
        
        # Get the ACL object
        acl_object = self.ensure(LENSE.OBJECTS.ACL.OBJECTS.get(uuid=target),
            error = 'Could not locate ACL object {0}'.format(target),
            debug = 'ACL object {0} exists, retrieved object'.format(target),
            code  = 404)
    
        # Make sure it has no child entries
        self.ensure(acl_object.objects, value=dict,
            error = 'Cannot delete ACL object {0}, contains child entries'.format(target),
            debug = 'ACL object {0} contains no children, delete OK'.format(target),
            code  = 400)

        # Delete the ACL object definition
        self.ensure(LENSE.OBJECTS.ACL.OBJECTS.delete(uuid=target),
            error = 'Failed to delete ACL {0}'.format(target),
            log   = 'Deleted ACL object {0}'.format(target),
            code  = 500)
        
        # Return the response
        return self.valid('Successfully deleted ACL object definition', {
            'uuid': target
        })

class ACLObjects_Create(RequestHandler):
    """
    Create a new ACL object definition.
    """  
    def launch(self):
        """
        Worker method for creating a new ACL object definition.
        """
        attrs = LENSE.REQUEST.map_data([
            'type', 
            'name', 
            'acl_mod', 
            'acl_cls', 
            'acl_key', 
            'obj_mod', 
            'obj_cls', 
            'obj_key',
            'def_acl'                            
        ])
        
        # Make sure the type definition is not already used
        self.ensure(LENSE.OBJECTS.ACL.OBJECTS.exists(**{'type': attrs['type']}), 
            value = False,
            error = 'ACL object type {0} already exists'.format(attrs['type']),
            code  = 400)
        
        # Validate the object module/class definitions
        for k in ['acl', 'obj']:
            mod = '{0}_mod'.format(k)
            cls = '{0}_cls'.format(k)
            self.ensure(self.mod_has_class(attrs[mod], attrs[cls], no_launch=True),
                error = 'Could not find object module/class',
                code  = 500)
        
        # Set a unique ID for the ACL object
        attrs['uuid'] = self.create_uuid()
        
        # If a default ACL UUID is supplied
        if self.get_data('def_acl', False):
            def_acl = self.ensure(LENSE.OBJECTS.ACL.KEYS.get(uuid=attrs['def_acl']),
                error = 'Default ACL {0} not found'.format(attrs['def_acl']),
                debug = 'Discovered default ACL key {0}'.format(attrs['def_acl']),
                code  = 404)
        
            # Get the default ACL key
            attrs['def_acl'] = def_acl
        
            # Make sure object level authentication is enabled
            self.ensure(def_acl.type_object, 
                error = 'Default ACL {0} must have object authentication enabled'.format(def_acl.uuid),
                code  = 400)
        
        # Create the ACL object
        self.ensure(LENSE.OBJECTS.ACL.OBJECTS.create(**attrs),
            error = 'Failed to create ACL object',
            log   = 'Created ACL object {0}'.format(attrs['uuid']),
            code  = 500)
        
        # Return the response
        return self.valid('Successfully created ACL object definition', {
            'type': attrs['type'],
            'uuid': attrs['uuid'],
            'name': attrs['name']
        })

class ACLObjects_Update(RequestHandler):
    """
    Update attributes for an ACL object.
    """
    def launch(self):
        """
        Worker method for updating an ACL object.
        """
        target = self.ensure(self.get_data('uuid', False),
            error = ERR_NO_UUID,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')),
            code  = 400)
        
        # Get the ACL object
        acl_object = self.ensure(LENSE.OBJECTS.ACL.get_objects(uuid=target),
            error = 'Could not locate ACL object type {0}'.format(target),
            debug = 'ACL object {0} exists, retrieved object'.format(target),
            code  = 404)

        # Delete the ACL object definition
        self.ensure(LENSE.OBJECTS.ACL.delete_object(uuid=target),
            error = 'Failed to delete ACL {0}'.format(target),
            log   = 'Deleted ACL object {0}'.format(target),
            code  = 500)
        
        # Return the response
        return self.valid('Successfully updated ACL object definition', {
            'uuid': target
        })
        
        # Make sure the object definition exists
        if not ACLObjects.objects.filter(**{'type': self.type}).count():
            return self.invalid('Failed to update ACL object, type definition [{0}] not found'.format(self.type))
        
        # Get the existing ACL object definition
        acl_obj = ACLObjects.objects.filter(**{'type': self.type}).values()[0]
        
        # ACL module / class
        acl_mod = acl_obj['acl_mod'] if not ('acl_mod' in LENSE.REQUEST.data) else self.get_data('acl_mod')
        acl_cls = acl_obj['acl_cls'] if not ('acl_cls' in LENSE.REQUEST.data) else self.get_data('acl_cls')
        
        # Make sure the module/class combination is valid
        acl_mod_status = self.mod_has_class(acl_mod, acl_cls, no_launch=True)
        if not acl_mod_status['valid']:
            return acl_mod_status
        
        # Object module / class
        obj_mod = acl_obj['obj_mod'] if not ('obj_mod' in LENSE.REQUEST.data) else self.get_data('obj_mod')
        obj_cls = acl_obj['obj_cls'] if not ('obj_cls' in LENSE.REQUEST.data) else self.get_data('obj_cls')
        
        # Make sure the module/class combination is valid
        obj_mod_status = self.mod_has_class(obj_mod, obj_cls, no_launch=True)
        if not obj_mod_status['valid']:
            return obj_mod_status
        
        # If updating the default ACL definition
        def_acl = None
        if 'def_acl' in LENSE.REQUEST.data:
            
            # Make sure the default ACL exists
            if not ACLKeys.objects.filter(uuid=self.get_data('def_acl')).count():
                return self.invalid('Failed to update ACL object type [{0}], default ACL [{1}] not found'.format(self.type, self.get_data('def_acl')))
        
            # Get the default ACL object
            def_acl = ACLKeys.objects.get(uuid=self.get_data('def_acl'))
            
            # Make sure the ACL has object type authentication enabled
            if not def_acl.type_object:
                return self.invalid('Failed to update ACL object type [{0}], default ACL [{1}] must have object authentication enabled'.format(self.type, def_acl.uuid))
        
            # Clear the UUID string from the API data
            self.clear_data('def_acl')
        
        # Update the object definition
        try:
            
            # Update string values
            ACLObjects.objects.filter(**{'type': self.type}).update(**LENSE.REQUEST.data)
            
            # If changing the default ACL
            if def_acl:
                acl_obj = ACLObjects.objects.get(**{'type': self.type})
                acl_obj.def_acl = def_acl
                acl_obj.save()
        
        # Critical error when updating ACL object definition
        except Exception as e:
            return self.invalid('Failed to update ACL object: {0}'.format(str(e)))
         
        # Successfully updated object
        return self.valid('Successfully updated ACL object')

class ACLObjects_Get(RequestHandler):
    """
    Retrieve a list of supported ACL object types.
    """
    def launch(self):
        """
        Worker method for returning a list of ACL object types.
        """
        target   = self.get_data('uuid', None)
        detailed = self.get_data('detailed', False)
        
        # Get all ACL objects
        if not target:
            return self.valid(LENSE.OBJECTS.ACL.OBJECTS.get())
        
        # Get the ACL object
        acl_object = self.ensure(LENSE.OBJECTS.ACL.OBJECTS.get(uuid=target),
            error = 'Could not locate ACL object {0}'.format(target),
            debug = 'ACL object {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the ACL object
        return self.valid(acl_object)
     
class ACLKeys_Update(RequestHandler):
    """
    Update an existing ACL definition.
    """ 
    def launch(self):
        """
        Worker method for updating an existing ACL definition.
        """
        target = self.ensure(self.get_data('uuid', False),
            error = ERR_NO_UUID,
            debug = 'Launching {0} for ACL keys object {1}'.format(__name__, self.get_data('uuid')),
            code  = 400)
        
        # Get the ACL key
        acl_key = self.ensure(LENSE.OBJECTS.ACL.OBJECTS.get(uuid=target),
            error = 'Could not locate ACL key {0}'.format(target),
            debug = 'ACL key {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # ACL parameters
        params = {
            'name': self.get_data('name', acl_row['name']),
            'desc': self.get_data('desc', acl_row['desc']),
            'type_object': self.get_data('type_object', acl_row['type_object']),
            'type_global': self.get_data('type_global', acl_row['type_global'])
        }
        
        # Update the ACL key
        self.ensure(LENSE.OBJECTS.ACL.KEYS.update(target, **params),
            error = 'Failed to update ACL key {0}'.format(target),
            log   = 'Updated ACL key {0}'.format(target),
            code  = 500)
        
        # If updating ACL handlers
        if self.get_data('handlers', None):
            _handlers = self.get_data('handler')
        
            # Get all handlers
            handlers  = LENSE.OBJECTS.HANDLER.get()
            
            # Only support one object type per ACL object access definition
            if 'object' in _handlers:
                obj_last = None
                for handler in handlers:
                    if (handler['uuid'] in handlers['object']) and (handler['object']):
                        if (obj_last == None) or (obj_last == handler['object']):
                            obj_last = handler['object']
                        else:
                            return self.invalid('Object type mismatch <{0} -> {1}>, ACLs only support one object type per definition.'.format(obj_last, handler['object']))
            
            # Get the current ACL object
            acl_obj = LENSE.OBJECTS.ACL.OBJECTS.get(uuid=target)
            
            # Update ACL handlers
            for acl_type, acl_handler in handlers.iteritems():
                    
                # Clear old definitions
                self.ensure(LENSE.OBJECTS.ACL.ACCESS(acl_type).delete(acl=target),
                    error = 'Failed to clear old ACL definitions',
                    debug = 'Cleared old ACL definitions',
                    code  = 500)
                
                # Create new definitions
                for handler in acl_handler:
                    self.ensure(LENSE.OBJECTS.ACL.ACCESS(acl_type).create(**{
                        'acl': acl_obj,
                        'handler': LENSE.OBJECTS.HANDLER.get(uuid=handler)
                    }), error = 'Failed to create new {0} ACL access definition'.format(acl_type),
                        debug = 'Created new {0} ACL access definition'.format(acl_type),
                        code  = 500)
                
        # ACL updated
        return self.valid('Succesfully updated ACL')
        
class ACLKeys_Delete(RequestHandler):
    """
    Delete an existing ACL key.
    """ 
    def launch(self):
        """
        Worker method for deleting an existing ACL.
        """
        target = self.ensure(self.get_data('uuid', False),
            error = ERR_NO_UUID,
            debug = 'Launching {0} for ACL key object {1}'.format(__name__, self.get_data('uuid')),
            code  = 400)
        
        # Make sure the ACL exists
        self.ensure(LENSE.OBJECTS.ACL.KEYS.exists(uuid=target),
            error = 'Cannot delete ACL {0}, does not exist'.format(target),
            code  = 404)
        
        # Delete the ACL key
        self.ensure(LENSE.OBJECTS.ACL.KEYS.delete(uuid=target),
            error = 'Failed to delete ACL key {0}'.format(target),
            log   = 'Deleted ACL key {0}'.format(target),
            code  = 500)
        
        # OK
        return self.valid('Successfully deleted ACL', {
            'uuid': target
        })
        
class ACLKeys_Create(RequestHandler):
    """
    Create a new ACL definition.
    """
    def launch(self):
        """
        Worker method for handling ACL definition creation.
        """
        
        # ACL key parameters
        params = {
            'uuid': self.create_uuid(),
            'name': self.get_data('name'),
            'desc': self.get_data('desc'),
            'type_object': self.get_data('type_object'),
            'type_global': self.get_data('type_global')
        }
        
        # Make sure the ACL doesn't exist
        self.ensure(LENSE.OBJECTS.ACL.KEYS.exists(name=params['name']),
            value = False,
            error = 'ACL key {0} is already defined'.format(params['name']),
            code  = 400)

        # Create the ACL key entry
        self.ensure(LENSE.OBJECTS.ACL.KEYS.create(**params),
            error = 'Failed to create ACL key {0}'.format(params['name']),
            log   = 'Created ACL key {0}'.format(params['name']),
            code  = 500)
            
        # Create ACL definition
        return self.valid('Create new ACL definition', {
            'uuid': params['uuid'],
            'name': params['name'],
            'desc': params['desc']
        })

class ACLKeys_Get(RequestHandler):
    """
    Return an object with all ACL definitions.
    """
    def launch(self):
        """
        Worker method used to construct the ACL definitions object.
        """
        target = self.get_data('uuid', None)
        
        # Get all ACL keys
        if not target:
            return self.valid(LENSE.OBJECTS.ACL.KEYS.get())
        
        # Get the ACL key
        acl_key = self.ensure(LENSE.OBJECTS.ACL.OBJECTS.get(uuid=target),
            error = 'Could not locate ACL key {0}'.format(target),
            debug = 'ACL key {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the ACL key
        return self.valid(acl_key)