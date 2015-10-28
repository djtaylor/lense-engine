import re
import json
import importlib

# Django Libraries
from django.db import models

# Lense Libraries
from lense.engine.api.objects.acl import ACLObjects
from lense.engine.api.app.gateway.models import DBGatewayACLGroupGlobalPermissions, \
                                                  DBGatewayACLKeys, \
                                                  DBGatewayACLGroupObjectUserPermissions, \
                                                  DBGatewayACLGroupObjectGroupPermissions

class DBGroupMembers(models.Model):
    """
    Database model that stores group membership.
    """
    group   = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='group')
    member  = models.ForeignKey('user.DBUser', to_field='uuid', db_column='member')
    
    # Custom model metadata
    class Meta:
        db_table = 'group_members'

class DBGroupDetailsQuerySet(models.query.QuerySet):
    """
    Custom queryset manager for the DBGroupDetails model. This allows customization of the returned
    QuerySet when extracting host details from the database.
    """
    def __init__(self, *args, **kwargs):
        super(DBGroupDetailsQuerySet, self).__init__(*args, **kwargs)
        
    def _object_permissions_get(self, group):
        """
        Construct a list of object permissions for hosts for this group.
        """
        
        # Process object permission flags
        def _process_flags(flags):
            ret_flags = {}
            for k,v in flags.iteritems():
                if not k in ret_flags:
                    ret_flags[k] = v
            return ret_flags
        
        # Construct the object permissions
        ret = {}
        for obj_details in ACLObjects.get_values():
            obj_type  = obj_details['type']
            obj_key   = '{0}_id'.format(obj_type)
            
            # Get an instance of the ACL class
            acl_def   = ACLObjects.get_values(obj_type)[0]
            acl_mod   = importlib.import_module(acl_def['acl_mod'])
            acl_class = getattr(acl_mod, acl_def['acl_cls'])
            
            print 'ACL_DEF: {0}'.format(acl_def)
            print 'ACL_MOD: {0}'.format(acl_mod)
            print 'ACL_CLS: {0}'.format(acl_class)
            
            # Get the object details
            try:
                acl_obj   = list(acl_class.objects.filter(owner=group['uuid']).values())
            except Exception as e:
                print 'YEP - FAILED: {0}'.format(str(e))
            
            print 'ACL_OBJ: {0}'.format(acl_obj)
            for acl in acl_obj:
                acl['object_id'] = acl[obj_key]
                del acl[obj_key]
            
            # Create the object permissions for this type
            ret[obj_type] = {
                'ids':     {},
                'details': acl_obj
            }
            
            # Set the object IDs
            for acl in acl_obj:
                obj_id = acl['object_id']
                if not obj_id in ret[obj_type]['ids']:
                    ret[obj_type]['ids'][obj_id] = []
                ret[obj_type]['ids'][obj_id].append(acl['acl_id'])
        
        # Return the constructed object permissions
        return ret
        
    def _global_permissions_get(self, group):
        """
        Construct a list of global permissions for this group.
        """
        global_permissions = []
        
        # Process each global permission definition for the group
        for global_permission in DBGatewayACLGroupGlobalPermissions.objects.filter(owner=group['uuid']).values():
            
            # Get the ACL details for this permission definition
            acl_details = DBGatewayACLKeys.objects.filter(uuid=global_permission['acl_id']).values()[0]
        
            # Update the return object
            global_permissions.append({
                'acl':      acl_details['name'],
                'uuid':     acl_details['uuid'],
                'desc':     acl_details['desc'],
                'allowed':  'yes' if global_permission['allowed'] else 'no'      
            })
            
        # Return the constructed permissions object
        return global_permissions
        
    def _extract_permissions(self, group):
        """
        Extract group permissions.
        """
        return {
            'global': self._global_permissions_get(group),
            'object': self._object_permissions_get(group)
        }
        
    def _extract_members(self, group):
        """
        Extract group members.
        """
        
        # Resolve circular dependencies
        from lense.engine.api.app.user.models import DBUser
        
        # Extract group membership
        members = []
        for member in list(DBGroupMembers.objects.filter(group=group['uuid']).values()):
            
            # Get the member user object
            user_obj = DBUser.objects.get(uuid=member['member_id'])
            members.append({
                'uuid':       user_obj.uuid,
                'username':   user_obj.username,
                'email':      user_obj.email,
                'is_enabled': user_obj.is_active,
                'fullname':   user_obj.get_full_name()
            })
            
        # Return the membership list
        return members
        
    def _extract(self, group):
        """
        Extract details for an API user group.
        """
        
        # Group membership / permissions
        group['members']     = self._extract_members(group)
        group['permissions'] = self._extract_permissions(group)
        
        # Return the constructed group object
        return group
        
    def values(self, detailed=False, *fields):
        """
        Wrapper for the default values() method.
        """
        
        # Store the initial results
        _r = super(DBGroupDetailsQuerySet, self).values(*fields)
        
        # Group return object
        _a = []
        
        # Process each group object definition
        for group in _r:
            _a.append(self._extract(group))
        
        # Return the constructed group results
        return _a

class DBGroupDetailsManager(models.Manager):
    """
    Custom objects manager for the DBGroupDetails model. Acts as a link between the main DBGroupDetails
    model and the custom DBGroupDetailsQuerySet model.
    """
    def __init__(self, *args, **kwargs):
        super(DBGroupDetailsManager, self).__init__()
    
    def get_queryset(self, *args, **kwargs):
        """
        Wrapper method for the internal get_queryset() method.
        """
        return DBGroupDetailsQuerySet(model=self.model)

class DBGroupDetails(models.Model):
    """
    Database model that contains API group information.
    """
    uuid      = models.CharField(max_length=36, unique=True)
    name      = models.CharField(max_length=64, unique=True)
    desc      = models.CharField(max_length=128)
    protected = models.NullBooleanField()
    
    # Custom objects manager
    objects   = DBGroupDetailsManager()
    
    def object_permissions_set(self, permissions):
        """
        Set object permissions for this group.
        """
    
        # Get a list of object types and details
        obj_types   = []
        obj_details = []
        for obj in ACLObjects.get_values():
            obj_types.append(obj['type'])
            obj_details.append(obj)
        
        # Process each object type in the request
        for obj_type in obj_types:
            if obj_type in permissions:
                
                # Get the details for this ACL object type
                obj_def   = ACLObjects.get_values(obj_type)[0]
                
                # Get an instance of the ACL class
                acl_mod   = importlib.import_module(obj_def['acl_mod'])
                acl_class = getattr(acl_mod, obj_def['acl_cls'])
                acl_key   = obj_def['acl_key']
                
                # Process each object
                for obj_id, obj_acls in permissions[obj_type].iteritems():
                
                    # Get an instance of the object class
                    obj_mod   = importlib.import_module(obj_def['obj_mod'])
                    obj_class = getattr(obj_mod, obj_def['obj_cls'])
                    obj_key   = obj_def['obj_key']
                
                    # Object filter
                    obj_filter = {}
                    obj_filter[obj_key] = obj_id
                
                    # Process each ACL definition
                    for acl_id, acl_val in obj_acls.iteritems():
                
                        # Define the filter dictionairy
                        filter = {}
                        filter['owner'] = self.uuid
                        filter['acl']   = acl_id
                        filter[acl_key] = obj_id
                    
                        # Revoke the permission
                        if acl_val == 'remove':
                            acl_class.objects.filter(**filter).delete()
                            
                        # Modify the permission
                        else:
                            
                            # If creating a new ACL entry
                            if not acl_class.objects.filter(**filter).count():
                                
                                # Model fields
                                fields = {}
                                fields['acl']     = DBGatewayACLKeys.objects.get(uuid=acl_id)
                                fields['owner']   = self
                                fields[obj_type]  = obj_class.objects.get(**obj_filter)
                                fields['allowed'] = acl_val
                                
                                # Create a new ACL entry
                                acl_class(**fields).save()
                                
                            # If updating an existing ACL entry
                            else:
                                obj = acl_class.objects.get(**filter)
                                obj.allowed = acl_val
                                obj.save()
                
    
    def global_permissions_set(self, permissions):
        """
        Set global permissions for this group.
        """
        
        # Get any existing global permissions
        gp_current = [x['acl_id'] for x in list(DBGatewayACLGroupGlobalPermissions.objects.filter(owner=self.uuid).values())]
        
        # Process each permission definition
        for key,value in permissions.iteritems():
            
            # If ACL already exists
            if key in gp_current:
                
                # If removing the ACL completely
                if value == 'remove':
                    DBGatewayACLGroupGlobalPermissions.objects.filter(owner=self.uuid, acl=key).delete()
                
                # If updating the ACL
                else:
                    acl = DBGatewayACLGroupGlobalPermissions.objects.get(owner=self.uuid, acl=key)
                    acl.allowed = value
                    acl.save()
                
            # If adding a new ACL
            else:
                acl = DBGatewayACLGroupGlobalPermissions(
                    acl     = DBGatewayACLKeys.objects.get(uuid=key),
                    owner   = self,
                    allowed = value
                )
                acl.save()
    
    def members_list(self):
        """
        Retrieve a compact list of group member names.
        """
        return [m['member_id'] for m in DBGroupMembers.objects.filter(group=self.uuid).values()]
    
    def members_get(self):
        """
        Retrieve a list of group member objects.
        """
        
        # Resolve circular dependencies
        from lense.engine.api.app.user.models import DBUser
        
        # Return a list of user member objects
        return [DBUser.objects.get(uuid=m.member) for m in DBGroupMembers.objects.filter(group=self.uuid)]
        
    def members_set(self, m):
        """
        Add a member to the group.
        """
        DBGroupMembers(group=self, member=m).save()
    
    def members_unset(self, m):
        """
        Remove a member from the group.
        """
        DBGroupMembers.objects.filter(group=self.uuid).filter(member=m.uuid).delete()
    
    # Custom model metadata
    class Meta:
        db_table = 'group_details'