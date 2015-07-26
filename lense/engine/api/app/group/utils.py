import re
import json
from uuid import uuid4

# Lense Libraries
from lense.common.utils import valid, invalid
from lense.common.vars import G_ADMIN, U_ADMIN
from lense.common.http import HTTP_GET
from lense.engine.api.app.user.models import DBUser
from lense.engine.api.app.group.models import DBGroupDetails, DBGroupMembers

class GroupMemberRemove:
    """
    API class designed to handle remove group members.
    """
    def __init__(self, parent):
        """
        Construct the GroupMemberRemove utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api   = parent

        # Target group / user
        self.group = self.api.acl.target_object() 
        self.user  = self.api.data['user']

    def launch(self):
        """
        Worker method that handles the removal of members from the group.
        """

        # Construct a list of authorized groups / users
        auth_groups = self.api.acl.authorized_objects('group', path='group', method=HTTP_GET)
        auth_users  = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)

        # If the group does not exist or access denied
        if not self.group in auth_groups.ids:
            return invalid('Failed to remove user <%s> from group <%s>, group not found or access denied' % (self.user, self.group))

        # If the user does not exist or access denied
        if not self.user in auth_users.ids:
            return invalid('Failed to remove user <%s> from group <%s>, user not found or access denied' % (self.user, self.group))
        
        # If trying to remove the default administrator account from the default administrator group
        if (self.user == U_ADMIN) and (self.group == G_ADMIN):
            return invalid('Cannot remove the default administrator account from the default administrator group')
        
        # Get the group object
        group = DBGroupDetails.objects.get(uuid=self.group)
        
        # Check if the user is already a member of the group
        if not self.user in group.members_list():
            return invalid('User <%s> is not a member of group <%s>' % (self.user, self.group))

        # Remove the user from the group
        group.members_unset(DBUser.objects.get(uuid=self.user))
        
        # Update the cached group data
        self.api.cache.save_object('group', self.group)
        
        # Return the response
        return valid('Successfully removed group member', {
            'group': {
                'name':   group.name,
                'uuid':   self.group,
                'member': self.user
            }
        })

class GroupMemberAdd:
    """
    API class designed to handle adding group members.
    """
    def __init__(self, parent):
        """
        Construct the GroupMemberAdd utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api   = parent

        # Target group / user
        self.group = self.api.acl.target_object() 
        self.user  = self.api.data['user']

    def launch(self):
        """
        Worker method that handles the addition of members to the group.
        """

        # Construct a list of authorized groups / users
        auth_groups = self.api.acl.authorized_objects('group', path='group', method=HTTP_GET)
        auth_users  = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)

        # If the group does not exist or access denied
        if not self.group in auth_groups.ids:
            return invalid('Failed to add user <%s> to group <%s>, group not found or access denied' % (self.user, self.group))

        # If the user does not exist or access denied
        if not self.user in auth_users.ids:
            return invalid('Failed to add user <%s> to group <%s>, user not found or access denied' % (self.user, self.group))
        
        # Get the group object
        group = DBGroupDetails.objects.get(uuid=self.group)
        
        # Check if the user is already a member of the group
        if self.user in group.members_list():
            return invalid('User <%s> is already a member of group <%s>' % (self.user, self.group))
        
        # Get the user object
        user = DBUser.objects.get(uuid=self.user)

        # Add the user to the group
        try:
            group.members_set(user)
            
        # Failed to add user to group
        except Exception as e:
            return invalid(self.api.log.exception('Failed to add user to group: %s' % str(e)))
        
        # Update the cached group data
        self.api.cache.save_object('group', self.group)
        
        # Return the response
        return valid('Successfully added group member', {
            'group': {
                'name':   group.name,
                'uuid':   self.group,
                'member': user.uuid
            }
        })

class GroupDelete:
    """
    API class designed to handle deleting groups.
    """
    def __init__(self, parent):
        """
        Construct the GroupDelete utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api   = parent

        # Target group
        self.group = self.api.acl.target_object()

    def launch(self):
        """
        Worker method that handles the deletion of the group.
        """

        # Construct a list of authorized groups
        auth_groups = self.api.acl.authorized_objects('group', path='group', method=HTTP_GET)

        # If the group does not exist or access denied
        if not self.group in auth_groups.ids:
            return invalid('Failed to delete group <%s>, not found in database or access denied' % self.group)

        # If the group is protected
        if auth_groups.extract(self.group)['protected']:
            return invalid('Failed to delete group <%s>, group is protected')

        # If the group has any members
        if DBGroupMembers.objects.filter(group=self.group).count():
            return invalid('Failed to delete group <%s>, must remove all group members first' % self.group)

        # Delete the group
        DBGroupDetails.objects.filter(uuid=self.group).delete()
        
        # Return the response
        return valid('Successfully deleted group', {
            'uuid': self.group
        })

class GroupUpdate:
    """
    API class designed to handle updating attributes and permissions for a group.
    """
    def __init__(self, parent):
        self.api         = parent

        # Group name change and return name value
        self.name_change = False
        self.name_return = None
        self.name_old    = None

        # Target group / group object
        self.group       = self.api.acl.target_object()
        self.group_obj   = None
    
    def _update_global_permissions(self):
        """
        Update the group global permissions.
        """
        if ('permissions' in self.api.data) and ('global' in self.api.data['permissions']):
            try:
                self.group_obj.global_permissions_set(self.api.data['permissions']['global'])
            except Exception as e:
                return invalid(self.api.log.exception('Failed to update global permissions: %s' % str(e)))
        return valid()
    
    def _update_object_permissions(self):
        """
        Update the group object permissions.
        """
        if ('permissions' in self.api.data) and ('object' in self.api.data['permissions']):
            try:
                self.group_obj.object_permissions_set(self.api.data['permissions']['object'])
            except Exception as e:
                return invalid(self.api.log.exception('Failed to update object permissions: %s' % str(e)))
        return valid()
    
    def _update_profile(self):
        """
        Update the group profile
        """
        if 'profile' in self.api.data:
            try:
                p = self.api.data['profile']
    
                # Changing group protected state
                if 'protected' in p:
                    if not (self.group_obj.protected == p['protected']):
                        
                        # Cannot disable protected for default administrator group
                        if (self.group == G_ADMIN) and (p['protected'] != True):
                            return invalid('Cannot disable the protected flag for the default administrator group')
                        
                        # Update the protected flag
                        self.group_obj.protected = p['protected']
                        self.group_obj.save()
    
                # Changing the group description
                if 'desc' in p:
                    if not (self.group_obj.desc == p['desc']):
                        self.group_obj.desc = p['desc']
                        self.group_obj.save()
        
                # Changing the group name
                if 'name' in p:
                    if not (self.group_obj.name == p['name']):
                        self.api.log.info('Renaming group <%s> to <%s>' % (self.group_obj.name, p['name']))
                        
                        # Toggle the name change flag and rename the group
                        self.name_change = True
                        self.name_old    = self.group_obj.name
                        self.group_obj.name = p['name']
                        self.group_obj.save()
                        
                        # Set the new group name to be returned
                        self.name_return = p['name']
            except Exception as e:
                return invalid(self.api.log.exception('Failed to update group profile: %s' % str(e)))
        else:
            self.name_return = self.group_obj.name
        return valid()
    
    def launch(self):
        """
        Worker method that handles updating group attributes.
        """
    
        # Construct a list of authorized groups
        auth_groups = self.api.acl.authorized_objects('group', path='group', method=HTTP_GET)

        # If the group does not exist or access denied
        if not self.group in auth_groups.ids:
            return invalid('Failed to update group <%s>, not found in database or access denied' % self.group)
        
        # Load the group object
        self.group_obj = DBGroupDetails.objects.get(uuid=self.group)
        
        # Update the group profile
        profile_status = self._update_profile()
        if not profile_status['valid']:
            return profile_status
        
        # Update global permissions
        gperms_status = self._update_global_permissions()
        if not gperms_status['valid']:
            return gperms_status
        
        # Update object permissions
        operms_status = self._update_object_permissions()
        if not operms_status['valid']:
            return operms_status
        
        # Update the cached group data
        self.api.cache.save_object('group', self.group)
        
        # Return the response
        return valid('Successfully updated group properties', {
            'name_change': self.name_change,
            'group_uuid':  self.group,
            'group_name':  self.name_return,
            'old_name':    False if not self.name_change else self.name_old
        })

class GroupCreate:
    """
    API class designed to handle the creation of groups.
    """
    def __init__(self, parent):
        """
        Construct the GroupCreate utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api   = parent

    def launch(self):
        """
        Worker method that handles the creation of the group.
        """
            
        # Make sure the group doesn't exist
        if DBGroupDetails.objects.filter(name=self.api.data['name']).count():
            return invalid(self.api.log.error('Group name <%s> already exists' % self.api.data['name']))
        
        # Generate a unique ID for the group
        group_uuid = str(uuid4())
        
        # If manually specifying a UUID
        if self.api.data.get('uuid', False):
            if DBGroupDetails.objects.filter(uuid=self.api.data['uuid']).count():
                return invalid(self.api.log.error('Cannot create group with duplicate UUID <%s>' % self.api.data['uuid']))
        
            # Set the manual UUID
            group_uuid = self.api.data['uuid']
            
        # Create the group
        try:
            DBGroupDetails(
                uuid      = group_uuid,
                name      = self.api.data['name'],
                desc      = self.api.data['desc'],
                protected = self.api.data.get('protected', False)
            ).save()
            
        # Failed to create group
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create group: %s' % str(e)))
        
        # Return the response
        return valid('Successfully created group', {
            'name':      self.api.data['name'],
            'desc':      self.api.data['desc'],
            'uuid':      str(group_uuid),
            'protected': self.api.data.get('protected', False)
        })

class GroupGet:
    """
    API class designed to retrieve the details of a single group, or a list of all group
    details.
    """
    def __init__(self, parent):
        """
        Construct the GroupGet utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api   = parent
        
        # Target group
        self.group = self.api.acl.target_object()
            
    def launch(self):
        """
        Worker method for retrieving group details.
        """
        
        # Construct a list of authorized groups
        auth_groups = self.api.acl.authorized_objects('group', path='group', method=HTTP_GET)
        
        # If retrieving details for a single group
        if self.group:
            
            # If the group does not exist or access denied
            if not self.group in auth_groups.ids:
                return invalid('Group <%s> not found or access denied' % self.group)
            
            # Return the group details
            return valid(auth_groups.extract(self.group))
            
        # If retrieving details for all groups
        else:
        
            # Return all groups
            return valid(auth_groups.details)
            