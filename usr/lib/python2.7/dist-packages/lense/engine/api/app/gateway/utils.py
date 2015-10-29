import re
import os
import json
from uuid import uuid4

# Django Libraries
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.utils import valid, invalid, mod_has_class
from lense.engine.api.auth.token import APIToken
from lense.engine.api.app.gateway.models import DBGatewayACLKeys, DBGatewayACLAccessGlobal, \
                                                  DBGatewayACLAccessObject, DBGatewayUtilities, DBGatewayACLObjects

class GatewayUtilitiesDelete:
    """
    Delete an existing API utility.
    """
    def __init__(self, parent):
        self.api = parent

        # Target utility
        self.utility = self.api.data['uuid']

    def launch(self):
        """
        Worker method used for deleting a utility.
        """
        
        # Make sure the utility exists
        if not DBGatewayUtilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not delete utility [{0}], not found in database'.format(self.utility)))
        
        # Get the utility details
        utility_row = DBGatewayUtilities.objects.filter(uuid=self.utility).values()[0]
        
        # Make sure the utility isn't protected
        if utility_row['protected']:
            return invalid('Cannot delete a protected utility')
        
        # Delete the utility
        try:
            DBGatewayUtilities.objects.filter(uuid=self.utility).delete()
        except Exception as e:
            return invalid(self.api.log.exeption('Failed to delete utility: {0}'.format(str(e))))
        
        # Construct and return the web data
        web_data = {
            'uuid': self.utility
        }
        return valid('Successfully deleted utility', web_data)

class GatewayUtilitiesCreate:
    """
    Create a new API utility.
    """
    def __init__(self, parent):
        self.api  = parent

    def _get_rmap(self):
        if isinstance(self.api.data['rmap'], (dict, list)):
            return json.dumps(self.api.data['rmap'])
        return self.api.data['rmap']

    def launch(self):
        """
        Worker method for creating a new utility.
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
        
        # Save the utility
        try:
            DBGatewayUtilities(**params).save()
            
            # Return the response
            return valid('Successfully created utility', {
                'uuid': params['uuid'],
                'path': params['path'],
                'method': params['method'],
                'desc': params['desc'],
                'enabled': params['enabled'],
                'protected': params['protected']
            })
            
        # Failed to save utility
        except Exception as e:
            return invalid('Failed to create utility: {0}'.format(str(e)))

class GatewayUtilitiesSave:
    """
    Save changes to an API utility.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target utility
        self.utility = self.api.data['uuid']

    def launch(self):
        """
        Worker method for saving changes to a utility.
        """

        # Make sure the utility exists
        if not DBGatewayUtilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not save utility [{0}], not found in database'.format(self.utility)))

        # Validate the utility attributes
        #util_status = self.api.util.GatewayUtilitiesValidate.launch()
        #if not util_status['valid']:
        #    return util_status

        # Get the utility details
        util_row = DBGatewayUtilities.objects.filter(uuid=self.utility).values()[0]
    
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

        # Attempt to update the utility
        try:
            DBGatewayUtilities.objects.filter(uuid=self.utility).update(**params)
            
        # Critical error when updating utility
        except Exception as e:
            return invalid(self.api.log.exception('Failed to update utility: {0}'.format(str(e))))

        # Successfully updated utility
        return valid('Successfully updated utility.')

class GatewayUtilitiesValidate:
    """
    Validate changes to an API utility prior to saving.
    """
    def __init__(self, parent):
        self.api = parent

        # Target utility
        self.utility = self.api.data['uuid']

    def _validate(self):
        """
        Validate the utility attributes.
        """
    
        # Get all utilities
        util_all = DBGatewayUtilities.objects.all().values()
    
        # ACL objects
        acl_objects  = list(DBGatewayACLObjects.objects.all().values())
    
        # Construct available external utilities
        util_ext = []
        for util in util_all:
            util_ext.append('%s.%s' % (util['mod'], util['cls']))
    
        # Get the utility details
        util_row = DBGatewayUtilities.objects.filter(uuid=self.utility).values()[0]
    
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
            return invalid('Failed to validate utility [{0}], invalid [path] value: {1}'.format(self.utility, default['path']))
    
        # Make sure the method is valid
        if not default['method'] in ['GET', 'POST', 'PUT', 'DELETE']:
            return invalid('Failed to validate utility [{0}], invalid [method] value: {1}'.format(self.utility, default['method']))
    
        # Make sure the object type is supported
        obj_supported = False if default['object'] else True
        for acl_obj in acl_objects:
            if acl_obj['type'] == object:
                obj_supported = True
                break
        if not obj_supported:
            return invalid('Failed to validate utility, using unsupported utility object type [{0}]'.format(object))
    
        # Make sure the request map is valid JSON
        try:
            tmp = json.loads(rmap)
        except Exception as e:
            return invalid('Failed to validate request map JSON: {0}'.format(str(e)))
    
        # Validate the module
        mod_path = mod.replace('.', '/')
        if not os.path.isfile('{0}/{1}.py'.format(MODULE_ROOT, mod_path)):
            return invalid('Failed to validate utility [{0}], module [{1}] not found'.format(self.utility, mod))
    
        # Validate the class
        mod_status = mod_has_class(mod, cls)
        if not mod_status['valid']:
            return mod_status
    
        # Validate external utilities
        for util in utils:
            if not util in util_ext:
                return invalid('Failed to validate utility [{0}], could not locate external utility class [{1}]'.format(self.utility, util))
        
        # Utility validated
        return valid()

    def launch(self):
        """
        Worker method for validating utility changes.
        """
        
        # Make sure the utility exists
        if not DBGatewayUtilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not validate utility [{0}], not found in database'.format(self.utility)))

        # Validate the utility attributes
        util_status = self._validate()
        if not util_status['valid']:
            return util_status
        
        # Utility is valid
        return valid('Utility validation succeeded.')

class GatewayUtilitiesClose:
    """
    Close an API utility and release the editing lock.
    """
    def __init__(self, parent):
        self.api = parent

        # Target utility
        self.utility = self.api.data['uuid']

    def launch(self):
        """
        Worker method for closing a utility and releasing the editing lock.
        """
    
        # Make sure the utility exists
        if not DBGatewayUtilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not check in utility [{0}], not found in database'.format(self.utility)))
        
        # Get the utility details row
        util_row = DBGatewayUtilities.objects.filter(uuid=self.utility).values()[0]
        
        # Check if the utility is already checked out
        if util_row['locked'] == False:
            return invalid(self.api.log.error('Could not check in utility [{0}], already checked in'.format(self.utility)))
        
        # Unlock the utility
        self.api.log.info('Checked in utility [{0}] by user [{1}]'.format(self.utility, self.api.user))
        try:
            DBGatewayUtilities.objects.filter(uuid=self.utility).update(
                locked    = False,
                locked_by = None
            )
            return valid('Successfully checked in utility')
            
        # Failed to check out the utility
        except Exception as e:
            return invalid(self.api.log.error('Failed to check in utility with error: {0}'.format(str(e))))

class GatewayUtilitiesOpen:
    """
    Open an API utility for editing.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target utility
        self.utility = self.api.data['uuid']
        
    def launch(self):
        """
        Worker method to open the utility for editing.
        """
        self.api.log.info('Preparing to checkout utility [{0}] for editing'.format(self.utility))
    
        # Make sure the utility exists
        if not DBGatewayUtilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not open utility [{0}] for editing, not found in database'.format(self.utility)))
        
        # Get the utility details row
        util_row = DBGatewayUtilities.objects.filter(uuid=self.utility).values()[0]
        
        # Check if the utility is locked
        if util_row['locked'] == True:
            self.api.log.info('Utility [{0}] already checked out by user [{1}]'.format(self.utility, util_row['locked_by']))
            
            # If the utility is checked out by the current user
            if util_row['locked_by'] == self.api.user:
                self.api.log.info('Utility checkout request OK, requestor [{0}] is the same as the locking user [{1}]'.format(self.api.user, util_row['locked_by']))
                return valid('Utility already checked out by the current user')
            else:
                return invalid(self.api.log.error('Could not open utility [{0}] for editing, already checked out by {1}'.format(self.utility, util_row['locked_by'])))
    
        # Set the locking user
        locked_by = self.api.user
        
        # Lock the utility for editing
        self.api.log.info('Checkout out utility [{0}] for editing by user [{1}]'.format(self.utility, locked_by))
        try:
            DBGatewayUtilities.objects.filter(uuid=self.utility).update(
                locked    = True,
                locked_by = self.api.user
            )
            return valid('Successfully checked out utility for editing')
            
        # Failed to check out the utility
        except Exception as e:
            return invalid(self.api.log.error('Failed to check out utility for editing with error: {0}'.format(str(e))))

class GatewayUtilitiesGet:
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
            
            # If grabbing a specific utility
            if 'uuid' in self.api.data:
                
                # If the utility doesn't exist
                if not DBGatewayUtilities.objects.filter(uuid=self.api.data['uuid']).count():
                    return invalid('Utility [{0}] does not exist'.format(self.api.data['uuid']))
                return valid(json.dumps(DBGatewayUtilities.objects.filter(uuid=self.api.data['uuid']).values()[0]))
                
            # Return all utilities
            else:
                return valid(json.dumps(list(DBGatewayUtilities.objects.all().values())))
        except Exception as e:
            return invalid(self.api.log.exception('Failed to retrieve utilities listing: {0}'.format(str(e))))

class GatewayACLObjectsDelete:
    """
    Delete an existing ACL object definition.
    """
    def __init__(self, parent):
        self.api  = parent
        
        # Get the target ACL object
        self.type = self.api.data.get('type')

    def launch(self):
        """
        Worker method for deleting an ACL object definition.
        """
        
        # If the ACL object doesn't exist
        if not DBGatewayACLObjects.objects.filter(type=self.type).count():
            return invalid('Cannot delete ACL object [{0}], not found in database'.format(self.type))
        
        # Get the ACL object definition
        acl_object = DBGatewayACLObjects.objects.filter(type=self.type).values(detailed=True)[0]
        
        # If the ACL object has any assigned object
        if acl_object['objects']:
            return invalid('Cannot delete ACL object [{0}] definition, contains [{1}] child objects'.format(self.type, str(len(acl_object['objects']))))

        # Delete the ACL object definition
        try:
            DBGatewayACLObjects.objects.filter(type=self.type).delete()
            
        # Critical error when deleting ACL object
        except Exception as e:
            return invalid(self.api.log.exception('Failed to delete ACL object [{0}] definition: {1}'.format(self.type, str(e))))

        # Return the response
        return valid('Successfully deleted ACL object definition', {
            'type': self.type
        })

class GatewayACLObjectsCreate:
    """
    Create a new ACL object definition.
    """
    def __init__(self, parent):
        self.api  = parent
        
        # API object attributes
        self.attr = self._set_attr()
        
    def _set_attr(self):
        """
        Set the attributes for the new ACL object.
        """
        
        # Attribute keys
        attr_keys = [
            'type', 
            'name', 
            'acl_mod', 
            'acl_cls', 
            'acl_key', 
            'obj_mod', 
            'obj_cls', 
            'obj_key',
            'def_acl'
        ]
        
        # Construct and return the attributes object
        return {k:self.api.data.get(k) for k in attr_keys}
        
    def launch(self):
        """
        Worker method for creating a new ACL object definition.
        """
        
        # Make sure the type definition is not already used
        if DBGatewayACLObjects.objects.filter(type=self.attr['type']).count():
            return invalid('Failed to create ACL object type [{0}], already defined'.format(self.attr['type']))
        
        # Check the ACL and object module/class definitions
        for key,status in {
            'acl': mod_has_class(self.attr['acl_mod'], self.attr['acl_cls'], no_launch=True),
            'obj': mod_has_class(self.attr['obj_mod'], self.attr['obj_cls'], no_launch=True)
        }.iteritems():
            if not status['valid']:
                return status
        
        # Set a unique ID for the ACL object
        self.attr['uuid'] = str(uuid4())
        
        # If a default ACL UUID is supplied
        if ('def_acl' in self.api.data):
            if not DBGatewayACLKeys.objects.filter(uuid=self.attr['def_acl']).count():
                return invalid('Failed to create ACL object type [{0}], default ACL [{1}] not found'.format(self.attr['type'], self.attr['def_acl']))
        
            # Get the default ACL object
            self.attr['def_acl'] = DBGatewayACLKeys.objects.get(uuid=self.api.data['def_acl'])
            
            # Make sure the ACL has object type authentication enabled
            if not self.attr['def_acl'].type_object:
                return invalid('Failed to create ACL object type [{0}], default ACL [{1}] must have object authentication enabled'.format(self.attr['type'], self.attr['def_acl']['uuid']))
        
        # Create the ACL object definition
        try:
            DBGatewayACLObjects(**self.attr).save()
            
        # Critical error when saving ACL object definition
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create ACL object type [{0}]: {1}'.format(self.attr['type'], str(e))))
        
        # Return the response
        return valid('Successfully created ACL object definition', {
            'type': self.attr['type'],
            'uuid': self.attr['uuid'],
            'name': self.attr['name']
        })

class GatewayACLObjectsUpdate:
    """
    Update attributes for an ACL object.
    """
    def __init__(self, parent): 
        self.api = parent

        # Target object type
        self.type = self.api.data.get('type')

    def launch(self):
        """
        Worker method for updating an ACL object.
        """
        
        # Make sure the object definition exists
        if not DBGatewayACLObjects.objects.filter(type=self.type).count():
            return invalid('Failed to update ACL object, type definition [{0}] not found'.format(self.type))
        
        # Get the existing ACL object definition
        acl_obj = DBGatewayACLObjects.objects.filter(type=self.type).values()[0]
        
        # ACL module / class
        acl_mod = acl_obj['acl_mod'] if not ('acl_mod' in self.api.data) else self.api.data['acl_mod']
        acl_cls = acl_obj['acl_cls'] if not ('acl_cls' in self.api.data) else self.api.data['acl_cls']
        
        # Make sure the module/class combination is valid
        acl_mod_status = mod_has_class(acl_mod, acl_cls, no_launch=True)
        if not acl_mod_status['valid']:
            return acl_mod_status
        
        # Object module / class
        obj_mod = acl_obj['obj_mod'] if not ('obj_mod' in self.api.data) else self.api.data['obj_mod']
        obj_cls = acl_obj['obj_cls'] if not ('obj_cls' in self.api.data) else self.api.data['obj_cls']
        
        # Make sure the module/class combination is valid
        obj_mod_status = mod_has_class(obj_mod, obj_cls, no_launch=True)
        if not obj_mod_status['valid']:
            return obj_mod_status
        
        # If updating the default ACL definition
        def_acl = None
        if 'def_acl' in self.api.data:
            
            # Make sure the default ACL exists
            if not DBGatewayACLKeys.objects.filter(uuid=self.api.data['def_acl']).count():
                return invalid('Failed to update ACL object type [{0}], default ACL [{1}] not found'.format(self.type, self.api.data['def_acl']))
        
            # Get the default ACL object
            def_acl = DBGatewayACLKeys.objects.get(uuid=self.api.data['def_acl'])
            
            # Make sure the ACL has object type authentication enabled
            if not def_acl.type_object:
                return invalid('Failed to update ACL object type [{0}], default ACL [{1}] must have object authentication enabled'.format(self.type, def_acl.uuid))
        
            # Clear the UUID string from the API data
            del self.api.data['def_acl']
        
        # Update the object definition
        try:
            
            # Update string values
            DBGatewayACLObjects.objects.filter(type=self.type).update(**self.api.data)
            
            # If changing the default ACL
            if def_acl:
                acl_obj = DBGatewayACLObjects.objects.get(type=self.type)
                acl_obj.def_acl = def_acl
                acl_obj.save()
        
        # Critical error when updating ACL object definition
        except Exception as e:
            return invalid('Failed to update ACL object: {0}'.format(str(e)))
         
        # Successfully updated object
        return valid('Successfully updated ACL object')

class GatewayACLObjectsGet:
    """
    Retrieve a list of supported ACL object types.
    """
    def __init__(self, parent):
        self.api      = parent

        # Type filter / detailed return
        self.type     = self.api.data.get('type')
        self.detailed = self.api.data.get('detailed')

        # Extract all ACL objects
        self.objects  = list(DBGatewayACLObjects.objects.all().values(detailed=self.detailed))

    def launch(self):
        """
        Worker method for returning a list of ACL object types.
        """
        
        # If retrieving a specific object type
        if self.type:
            object_details = [x for x in self.objects if x['type'] == self.type]
            
            # Make sure the object type exists
            if not object_details:
                return invalid('Could not locate ACL object of type [{0}] in the database'.format(self.type))
            
            # Return the ACL object
            return valid(object_details[0])
        
        # Retrieving all ACL object definitions
        else:
            
            # Return ACL object definitions
            return valid(self.objects)
     
class GatewayACLUpdate:
    """
    Update an existing ACL definition.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target ACL
        self.acl = self.api.data['uuid']
        
    def launch(self):
        """
        Worker method for updating an existing ACL definition.
        """
        
        # Make sure the ACL exists
        if not DBGatewayACLKeys.objects.filter(uuid=self.acl).count():
            return invalid('Failed to update ACL [{0}], not found in database'.format(self.acl))
        
        # Get the ACL details
        acl_row  = DBGatewayACLKeys.objects.filter(uuid=self.acl).values()[0]
        
        # ACL parameters
        params = {
            'name': self.api.data.get('name', acl_row['name']),
            'desc': self.api.data.get('desc', acl_row['desc']),
            'type_object': self.api.data.get('type_object', acl_row['type_object']),
            'type_global': self.api.data.get('type_global', acl_row['type_global'])
        }
        
        # Update ACL details
        try:
            DBGatewayACLKeys.objects.filter(uuid=self.acl).update(**params)
            self.api.log.info('Updated properties for ACL [{0}]'.format(self.acl))
        except Exception as e:
            return invalid(self.api.log.exception('Failed to update details for ACL [{0}]: {1}'.format(self.acl, str(e))))
        
        # If updating ACL utilities
        if 'utilities' in self.api.data:
            utilities     = self.api.data['utilities']
            
            # Get all utilities
            util_all = list(DBGatewayUtilities.objects.all().values())
            
            # Only support one object type per ACL object access definition
            if 'object' in utilities:
                obj_last = None
                for util in util_all:
                    if (util['uuid'] in utilities['object']) and (util['object']):
                        if (obj_last == None) or (obj_last == util['object']):
                            obj_last = util['object']
                        else:
                            return invalid('Object type mismatch <{0} -> {1}>, ACLs only support one object type per definition.'.format(obj_last, util['object']))
            
            # Get the current ACL object
            acl_obj = DBGatewayACLKeys.objects.get(uuid=self.acl)
            
            # Update ACL utilities
            for acl_type, acl_util in utilities.iteritems():
                self.api.log.info('Updating access type [{0}] for ACL [{1}]'.format(acl_type, self.acl))
                try:
                    
                    # Global
                    if acl_type == 'global':
                        
                        # Clear old definitions
                        DBGatewayACLAccessGlobal.objects.filter(acl=self.acl).delete()
                        
                        # Put in new definitions
                        for util in acl_util:
                            DBGatewayACLAccessGlobal(
                                acl     = acl_obj,
                                utility = DBGatewayUtilities.objects.get(uuid=util)
                            ).save()
                    
                    # Object
                    if acl_type == 'object':
                        
                        # Clear old definitions
                        DBGatewayACLAccessObject.objects.filter(acl=self.acl).delete()
                        
                        # Put in new definitions
                        for util in acl_util:
                            DBGatewayACLAccessObject(
                                acl     = acl_obj,
                                utility = DBGatewayUtilities.objects.get(uuid=util)
                            ).save()
                    
                    # All utilities updated
                    self.api.log.info('Updated all utilities for ACL [{0}]'.format(self.acl))
                    
                # Failed to update utilities
                except Exception as e:
                    return invalid(self.api.log.exception('Failed to update [{0}] utilities for ACL [{1}]: {2}'.format(acl_type, self.acl, str(e))))
        
        # ACL updated
        return valid('Succesfully updated ACL')
        
class GatewayACLDelete:
    """
    Delete an existing ACL.
    """            
    def __init__(self, parent):
        self.api = parent
        
        # Target ACL
        self.acl = self.api.data['uuid']
        
    def launch(self):
        """
        Worker method for deleting an existing ACL.
        """
        
        # Make sure the ACL exists
        if not DBGatewayACLKeys.objects.filter(uuid=self.acl).count():
            return invalid('Failed to delete ACL [{0}], not found in database'.format(self.acl))
        
        # Delete the ACL definition
        try:
            DBGatewayACLKeys.objects.filter(uuid=self.acl).delete()
            self.api.log.info('Deleted ACL definition [{0}]'.format(self.acl))
            
            # ACL deleted
            return valid('Successfully deleted ACL', {
                'uuid': self.acl
            })
            
        # Failed to delete ACL
        except Exception as e:
            return invalid(self.api.log.exception('Failed to delete ACL [{0}]: {1}'.format(self.acl, str(e))))
        
class GatewayACLCreate:
    """
    Create a new ACL definition.
    """
    def __init__(self, parent):
        self.api = parent
        
    def launch(self):
        """
        Worker method for handling ACL definition creation.
        """
        
        # Generate a UUID for the ACL
        acl_uuid = str(uuid4())
        
        # Utilities (not used for now)
        #utils = self.api.data['utilities']
        
        # ACL parameters
        params = {
            'uuid': str(uuid4()),
            'name': self.api.data['name'],
            'desc': self.api.data['desc'],
            'type_object': self.api.data['type_object'],
            'type_global': self.api.data['type_global']
        }
        
        # Make sure the ACL doesn't exist
        if DBGatewayACLKeys.objects.filter(name=params['name']).count():
            return invalid('ACL [{0}] is already defined'.format(acl_name))

        # Create the ACL key entry
        try:
            DBGatewayACLKeys(**params).save()
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create ACL definition: {0}'.format(str(e))))
            
        # Create ACL definition
        return valid('Create new ACL definition', {
            'uuid': params['uuid'],
            'name': params['name'],
            'desc': params['desc']
        })

class GatewayACLGet:
    """
    Return an object with all ACL definitions.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Target ACL definition
        self.acl = self.api.acl.target_object()

    def launch(self):
        """
        Worker method used to construct the ACL definitions object.
        """
        
        # Construct the ACL object
        try:
            
            # If retrieving a single ACL definition
            if self.acl:
                
                # Get the ACL definition
                acl_definition = DBGatewayACLKeys.objects.filter(uuid=self.acl).values()
                
                # If the ACL definition doesn't exist
                if not acl_definition:
                    return invalid('Could not locate ACL [{0}] in the database'.format(self.acl))
                
                # Return the ACL definition
                return valid(json.dumps(acl_definition[0]))
            
            # If retrieving all ACL definitions
            else:
                return valid(json.dumps(list(DBGatewayACLKeys.objects.all().values())))
            
        # Error during ACL construction
        except Exception as e:
            return invalid(self.api.log.exception('Failed to retrieve ACL definition(s): {0}'.format(str(e))))

class GatewayTokenGet:
    """
    Class used to handle token requests.
    """
    def __init__(self, parent):
        self.api = parent
        
    def launch(self):
        """
        Worker method used to process token requests and return a token if the API
        key is valid and authorized.
        """
        
        # Get the API token
        api_token = APIToken().get(id=self.api.request.user)
        
        # Handle token retrieval errors
        if api_token == False:
            return invalid(self.api.log.error('Error retreiving API token for user [{0}]'.format(self.api.request.user)))
        else:
            
            # Return the API token
            return valid({'token': api_token})