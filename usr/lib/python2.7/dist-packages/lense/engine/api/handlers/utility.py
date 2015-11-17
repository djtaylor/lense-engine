import re
import os
import json
from uuid import uuid4

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.objects.acl.models import ACLObjects
from lense.common.objects.utility.models import Utilities
from lense.common.utils import valid, invalid, mod_has_class

class Utility_Delete:
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
        if not Utilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not delete utility [{0}], not found in database'.format(self.utility)))
        
        # Get the utility details
        utility_row = Utilities.objects.filter(uuid=self.utility).values()[0]
        
        # Make sure the utility isn't protected
        if utility_row['protected']:
            return invalid('Cannot delete a protected utility')
        
        # Delete the utility
        try:
            Utilities.objects.filter(uuid=self.utility).delete()
        except Exception as e:
            return invalid(self.api.log.exeption('Failed to delete utility: {0}'.format(str(e))))
        
        # Construct and return the web data
        web_data = {
            'uuid': self.utility
        }
        return valid('Successfully deleted utility', web_data)

class Utility_Create:
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
            Utilities(**params).save()
            
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

class Utility_Save:
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
        if not Utilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not save utility [{0}], not found in database'.format(self.utility)))

        # Validate the utility attributes
        #util_status = self.api.util.GatewayUtilitiesValidate.launch()
        #if not util_status['valid']:
        #    return util_status

        # Get the utility details
        util_row = Utilities.objects.filter(uuid=self.utility).values()[0]
    
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
            Utilities.objects.filter(uuid=self.utility).update(**params)
            
        # Critical error when updating utility
        except Exception as e:
            return invalid(self.api.log.exception('Failed to update utility: {0}'.format(str(e))))

        # Successfully updated utility
        return valid('Successfully updated utility.')

class Utility_Validate:
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
        util_all = Utilities.objects.all().values()
    
        # ACL objects
        acl_objects  = list(ACLObjects.objects.all().values())
    
        # Construct available external utilities
        util_ext = []
        for util in util_all:
            util_ext.append('%s.%s' % (util['mod'], util['cls']))
    
        # Get the utility details
        util_row = Utilities.objects.filter(uuid=self.utility).values()[0]
    
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
        if not Utilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not validate utility [{0}], not found in database'.format(self.utility)))

        # Validate the utility attributes
        util_status = self._validate()
        if not util_status['valid']:
            return util_status
        
        # Utility is valid
        return valid('Utility validation succeeded.')

class Utility_Close:
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
        if not Utilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not check in utility [{0}], not found in database'.format(self.utility)))
        
        # Get the utility details row
        util_row = Utilities.objects.filter(uuid=self.utility).values()[0]
        
        # Check if the utility is already checked out
        if util_row['locked'] == False:
            return invalid(self.api.log.error('Could not check in utility [{0}], already checked in'.format(self.utility)))
        
        # Unlock the utility
        self.api.log.info('Checked in utility [{0}] by user [{1}]'.format(self.utility, self.api.user))
        try:
            Utilities.objects.filter(uuid=self.utility).update(
                locked    = False,
                locked_by = None
            )
            return valid('Successfully checked in utility')
            
        # Failed to check out the utility
        except Exception as e:
            return invalid(self.api.log.error('Failed to check in utility with error: {0}'.format(str(e))))

class Utility_Open:
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
        if not Utilities.objects.filter(uuid=self.utility).count():
            return invalid(self.api.log.error('Could not open utility [{0}] for editing, not found in database'.format(self.utility)))
        
        # Get the utility details row
        util_row = Utilities.objects.filter(uuid=self.utility).values()[0]
        
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
            Utilities.objects.filter(uuid=self.utility).update(
                locked    = True,
                locked_by = self.api.user
            )
            return valid('Successfully checked out utility for editing')
            
        # Failed to check out the utility
        except Exception as e:
            return invalid(self.api.log.error('Failed to check out utility for editing with error: {0}'.format(str(e))))

class Utility_Get:
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
                if not Utilities.objects.filter(uuid=self.api.data['uuid']).count():
                    return invalid('Utility [{0}] does not exist'.format(self.api.data['uuid']))
                return valid(json.dumps(Utilities.objects.filter(uuid=self.api.data['uuid']).values()[0]))
                
            # Return all utilities
            else:
                return valid(json.dumps(list(Utilities.objects.all().values())))
        except Exception as e:
            return invalid(self.api.log.exception('Failed to retrieve utilities listing: {0}'.format(str(e))))