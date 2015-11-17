import re
import os
import json
from uuid import uuid4

# Django Libraries
from django.core.serializers.json import DjangoJSONEncoder

# Lense Libraries
from lense import MODULE_ROOT
from lense.common.objects.utility.models import Utilities
from lense.common.utils import valid, invalid, mod_has_class
from lense.common.objects.acl.models import ACLKeys, ACLObjects, ACLGlobalAccess, ACLObjectAccess

class ACLObjects_Delete:
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
        if not ACLObjects.objects.filter(type=self.type).count():
            return invalid('Cannot delete ACL object [{0}], not found in database'.format(self.type))
        
        # Get the ACL object definition
        acl_object = ACLObjects.objects.filter(type=self.type).values(detailed=True)[0]
        
        # If the ACL object has any assigned object
        if acl_object['objects']:
            return invalid('Cannot delete ACL object [{0}] definition, contains [{1}] child objects'.format(self.type, str(len(acl_object['objects']))))

        # Delete the ACL object definition
        try:
            ACLObjects.objects.filter(type=self.type).delete()
            
        # Critical error when deleting ACL object
        except Exception as e:
            return invalid(self.api.log.exception('Failed to delete ACL object [{0}] definition: {1}'.format(self.type, str(e))))

        # Return the response
        return valid('Successfully deleted ACL object definition', {
            'type': self.type
        })

class ACLObjects_Create:
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
        if ACLObjects.objects.filter(type=self.attr['type']).count():
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
            if not ACLKeys.objects.filter(uuid=self.attr['def_acl']).count():
                return invalid('Failed to create ACL object type [{0}], default ACL [{1}] not found'.format(self.attr['type'], self.attr['def_acl']))
        
            # Get the default ACL object
            self.attr['def_acl'] = ACLKeys.objects.get(uuid=self.api.data['def_acl'])
            
            # Make sure the ACL has object type authentication enabled
            if not self.attr['def_acl'].type_object:
                return invalid('Failed to create ACL object type [{0}], default ACL [{1}] must have object authentication enabled'.format(self.attr['type'], self.attr['def_acl']['uuid']))
        
        # Create the ACL object definition
        try:
            ACLObjects(**self.attr).save()
            
        # Critical error when saving ACL object definition
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create ACL object type [{0}]: {1}'.format(self.attr['type'], str(e))))
        
        # Return the response
        return valid('Successfully created ACL object definition', {
            'type': self.attr['type'],
            'uuid': self.attr['uuid'],
            'name': self.attr['name']
        })

class ACLObjects_Update:
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
        if not ACLObjects.objects.filter(type=self.type).count():
            return invalid('Failed to update ACL object, type definition [{0}] not found'.format(self.type))
        
        # Get the existing ACL object definition
        acl_obj = ACLObjects.objects.filter(type=self.type).values()[0]
        
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
            if not ACLKeys.objects.filter(uuid=self.api.data['def_acl']).count():
                return invalid('Failed to update ACL object type [{0}], default ACL [{1}] not found'.format(self.type, self.api.data['def_acl']))
        
            # Get the default ACL object
            def_acl = ACLKeys.objects.get(uuid=self.api.data['def_acl'])
            
            # Make sure the ACL has object type authentication enabled
            if not def_acl.type_object:
                return invalid('Failed to update ACL object type [{0}], default ACL [{1}] must have object authentication enabled'.format(self.type, def_acl.uuid))
        
            # Clear the UUID string from the API data
            del self.api.data['def_acl']
        
        # Update the object definition
        try:
            
            # Update string values
            ACLObjects.objects.filter(type=self.type).update(**self.api.data)
            
            # If changing the default ACL
            if def_acl:
                acl_obj = ACLObjects.objects.get(type=self.type)
                acl_obj.def_acl = def_acl
                acl_obj.save()
        
        # Critical error when updating ACL object definition
        except Exception as e:
            return invalid('Failed to update ACL object: {0}'.format(str(e)))
         
        # Successfully updated object
        return valid('Successfully updated ACL object')

class ACLObjects_Get:
    """
    Retrieve a list of supported ACL object types.
    """
    def __init__(self, parent):
        self.api      = parent

        # Type filter / detailed return
        self.type     = self.api.data.get('type')
        self.detailed = self.api.data.get('detailed')

        # Extract all ACL objects
        self.objects  = list(ACLObjects.objects.all().values(detailed=self.detailed))

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
     
class ACL_Update:
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
        if not ACLKeys.objects.filter(uuid=self.acl).count():
            return invalid('Failed to update ACL [{0}], not found in database'.format(self.acl))
        
        # Get the ACL details
        acl_row  = ACLKeys.objects.filter(uuid=self.acl).values()[0]
        
        # ACL parameters
        params = {
            'name': self.api.data.get('name', acl_row['name']),
            'desc': self.api.data.get('desc', acl_row['desc']),
            'type_object': self.api.data.get('type_object', acl_row['type_object']),
            'type_global': self.api.data.get('type_global', acl_row['type_global'])
        }
        
        # Update ACL details
        try:
            ACLKeys.objects.filter(uuid=self.acl).update(**params)
            self.api.log.info('Updated properties for ACL [{0}]'.format(self.acl))
        except Exception as e:
            return invalid(self.api.log.exception('Failed to update details for ACL [{0}]: {1}'.format(self.acl, str(e))))
        
        # If updating ACL utilities
        if 'utilities' in self.api.data:
            utilities     = self.api.data['utilities']
            
            # Get all utilities
            util_all = list(Utilities.objects.all().values())
            
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
            acl_obj = ACLKeys.objects.get(uuid=self.acl)
            
            # Update ACL utilities
            for acl_type, acl_util in utilities.iteritems():
                self.api.log.info('Updating access type [{0}] for ACL [{1}]'.format(acl_type, self.acl))
                try:
                    
                    # Global
                    if acl_type == 'global':
                        
                        # Clear old definitions
                        ACLGlobalAccess.objects.filter(acl=self.acl).delete()
                        
                        # Put in new definitions
                        for util in acl_util:
                            ACLGlobalAccess(
                                acl     = acl_obj,
                                utility = Utilities.objects.get(uuid=util)
                            ).save()
                    
                    # Object
                    if acl_type == 'object':
                        
                        # Clear old definitions
                        ACLObjectAccess.objects.filter(acl=self.acl).delete()
                        
                        # Put in new definitions
                        for util in acl_util:
                            ACLObjectAccess(
                                acl     = acl_obj,
                                utility = Utilities.objects.get(uuid=util)
                            ).save()
                    
                    # All utilities updated
                    self.api.log.info('Updated all utilities for ACL [{0}]'.format(self.acl))
                    
                # Failed to update utilities
                except Exception as e:
                    return invalid(self.api.log.exception('Failed to update [{0}] utilities for ACL [{1}]: {2}'.format(acl_type, self.acl, str(e))))
        
        # ACL updated
        return valid('Succesfully updated ACL')
        
class ACL_Delete:
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
        if not ACLKeys.objects.filter(uuid=self.acl).count():
            return invalid('Failed to delete ACL [{0}], not found in database'.format(self.acl))
        
        # Delete the ACL definition
        try:
            ACLKeys.objects.filter(uuid=self.acl).delete()
            self.api.log.info('Deleted ACL definition [{0}]'.format(self.acl))
            
            # ACL deleted
            return valid('Successfully deleted ACL', {
                'uuid': self.acl
            })
            
        # Failed to delete ACL
        except Exception as e:
            return invalid(self.api.log.exception('Failed to delete ACL [{0}]: {1}'.format(self.acl, str(e))))
        
class ACL_Create:
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
        if ACLKeys.objects.filter(name=params['name']).count():
            return invalid('ACL [{0}] is already defined'.format(acl_name))

        # Create the ACL key entry
        try:
            ACLKeys(**params).save()
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create ACL definition: {0}'.format(str(e))))
            
        # Create ACL definition
        return valid('Create new ACL definition', {
            'uuid': params['uuid'],
            'name': params['name'],
            'desc': params['desc']
        })

class ACL_Get:
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
                acl_definition = ACLKeys.objects.filter(uuid=self.acl).values()
                
                # If the ACL definition doesn't exist
                if not acl_definition:
                    return invalid('Could not locate ACL [{0}] in the database'.format(self.acl))
                
                # Return the ACL definition
                return valid(json.dumps(acl_definition[0]))
            
            # If retrieving all ACL definitions
            else:
                return valid(json.dumps(list(ACLKeys.objects.all().values())))
            
        # Error during ACL construction
        except Exception as e:
            return invalid(self.api.log.exception('Failed to retrieve ACL definition(s): {0}'.format(str(e))))

