import re
import json
from uuid import uuid4

# Lense Libraries
from lense.common.http import HTTP_GET
from lense.common.vars import GROUPS, USERS
from lense.common.utils import valid, invalid
from lense.engine.api.handlers import RequestHandler
from lense.common.objects.group.models import APIGroupMembers

ERR_NO_UUID='No group UUID found in request data'

class GroupMember_Remove(RequestHandler):
    """
    API class designed to handle remove group members.
    """
    def launch(self):
        """
        Worker method that handles the removal of members from the group.
        """
        
        # Target group
        group = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('group', False),
            error = 'No group UUID found in request data',
            code  = 400)
        
        # Target user
        user = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('user', False),
            error = 'No user UUID found in request data',
            code  = 400)

        # Get the group object
        group = LENSE.REQUEST.ensure(LENSE.OBJECTS.GROUP.get(uuid=group),
            error = 'Could not locate group object {0}'.format(group),
            debug = 'Group object {0} exists, retrieved object'.format(group),
            code  = 404)

        # Cannot remove admin user from admin group
        remove_admin = False if not (user.uuid == USERS.ADMIN.UUID) and not (group == GROUPS.ADMIN.UUID) else True

        # Cannot remove the default administrator user from administrator group
        LENSE.REQUEST.ensure(remove_admin,
            value = False,
            error = 'Cannot remove administrator account from administrator group',
            code  = 500)
        
        # Check if the user is already a member of the group
        LENSE.REQUEST.ensure(LENSE.GROUP.has_members(group.uuid, user.uuid),
            error = 'User {0} is not a member of group {1}'.format(user.uuid, group.uuid),
            code  = 400)
        
        # Remove the user from the group
        LENSE.REQUEST.ensure(LENSE.GROUP.remove_member(group.uuid, user.uuid),
            error = 'Failed to remove user {0} from group {1}'.format(user.uuid, group.uuid),
            log   = 'Removed user {0} from group {1}'.format(user.uuid, group.uuid),
            code  = 500)
        
        # Return the response
        return valid('Successfully removed group member', {
            'group': {
                'name':   group.name,
                'uuid':   group.uuid,
                'member': user.uuid
            }
        })

class GroupMember_Add(RequestHandler):
    """
    API class designed to handle adding group members.
    """
    def launch(self):
        """
        Worker method that handles the addition of members to the group.
        """
        
        # Target group
        group = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('group', False),
            error = 'No group UUID found in request data',
            code  = 400)
        
        # Target user
        user = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('user', False),
            error = 'No user UUID found in request data',
            code  = 400)

        # Get the group object
        group = LENSE.REQUEST.ensure(LENSE.OBJECTS.GROUP.get(uuid=group),
            error = 'Could not locate group object {0}'.format(group),
            debug = 'Group object {0} exists, retrieved object'.format(group),
            code  = 404)
        
        # Check if the user is already a member of the group
        LENSE.REQUEST.ensure(LENSE.GROUP.has_members(group.uuid, user.uuid),
            value = False,
            error = 'User {0} is already a member of group {1}'.format(user.uuid, group.uuid),
            code  = 400)

        # Add the user to the group
        LENSE.REQUEST.ensure(LENSE.GROUP.add_member(group.uuid, user.uuid),
            error = 'Failed to add user {0} to group {1}'.format(user.uuid, group.uuid),
            log   = 'Added user {0} to group {1}'.format(user.uuid, group.uuid),
            code  = 500)
        
        # Return the response
        return valid('Successfully added group member', {
            'group': {
                'name':   group.name,
                'uuid':   group.uuid,
                'member': user.uuid
            }
        })

class Group_Delete(RequestHandler):
    """
    API class designed to handle deleting groups.
    """
    def launch(self):
        """
        Worker method that handles the deletion of the group.
        """
        target = LENSE.REQUEST.ensure(LENSE.REQUEST.data.get('uuid', False),
            error = ERR_NO_UUID,
            debug = 'Launching {0} for group object {1}'.format(__name__, LENSE.REQUEST.data['uuid']),
            code  = 400)

        # Get the group
        group = LENSE.REQUEST.ensure(LENSE.GROUP.get(target),
            error = 'Could not locate group object {0}'.format(target),
            debug = 'Group object {0} exists, retrieved object'.format(target),
            code  = 404)

        # Make sure the group isn't protected
        LENSE.REQUEST.ensure(group.protected, 
            value = False,
            error = 'Cannot deleted protected group {0}'.format(group.uuid),
            code  = 400)

        # Make sure the group has no members
        LENSE.REQUEST.ensure(LENSE.GROUP.has_members(group.uuid),
            value = False,
            error = 'Cannot delete group {0}, still has members'.format(group.uuid),
            code  = 400)

        # Delete the group
        LENSE.GROUP.delete(group.uuid)
        
        # Return the response
        return valid('Successfully deleted group', {
            'uuid': group.uuid
        })

class Group_Update(RequestHandler):
    """
    API class designed to handle updating attributes and permissions for a group.
    """
    def __init__(self):

        # Group name change and return name value
        self.name_change = False
        self.name_return = None
        self.name_old    = None

        # Target group / group object
        self.group       = LENSE.AUTH.ACL.target_object()
        self.group_obj   = None
    
    def _update_global_permissions(self):
        """
        Update the group global permissions.
        """
        if ('permissions' in LENSE.REQUEST.data) and ('global' in LENSE.REQUEST.data['permissions']):
            try:
                self.group_obj.global_permissions_set(LENSE.REQUEST.data['permissions']['global'])
            except Exception as e:
                return invalid(LENSE.API.LOG.exception('Failed to update global permissions: {0}'.format(str(e))))
        return valid()
    
    def _update_object_permissions(self):
        """
        Update the group object permissions.
        """
        if ('permissions' in LENSE.REQUEST.data) and ('object' in LENSE.REQUEST.data['permissions']):
            try:
                self.group_obj.object_permissions_set(LENSE.REQUEST.data['permissions']['object'])
            except Exception as e:
                return invalid(LENSE.API.LOG.exception('Failed to update object permissions: {0}'.format(str(e))))
        return valid()
    
    def _update_profile(self):
        """
        Update the group profile
        """
        if 'profile' in LENSE.REQUEST.data:
            try:
                p = LENSE.REQUEST.data['profile']
    
                # Changing group protected state
                if 'protected' in p:
                    if not (self.group_obj.protected == p['protected']):
                        
                        # Cannot disable protected for default administrator group
                        if (self.group == GROUPS.ADMIN.UUID) and (p['protected'] != True):
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
                        LENSE.API.LOG.info('Renaming group <{0}> to <{1}>'.format(self.group_obj.name, p['name']))
                        
                        # Toggle the name change flag and rename the group
                        self.name_change = True
                        self.name_old    = self.group_obj.name
                        self.group_obj.name = p['name']
                        self.group_obj.save()
                        
                        # Set the new group name to be returned
                        self.name_return = p['name']
            except Exception as e:
                return invalid(LENSE.API.LOG.exception('Failed to update group profile: {0}'.format(str(e))))
        else:
            self.name_return = self.group_obj.name
        return valid()
    
    def launch(self):
        """
        Worker method that handles updating group attributes.
        """
    
        # Construct a list of authorized groups
        auth_groups = LENSE.AUTH.ACL.authorized_objects('group', path='group', method=HTTP_GET)

        # If the group does not exist or access denied
        if not self.group in auth_groups.ids:
            return invalid('Failed to update group <{0}>, not found in database or access denied'.format(self.group))
        
        # Load the group object
        self.group_obj = LENSE.GROUP.get(self.group)
        
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
        
        # Return the response
        return valid('Successfully updated group properties', {
            'name_change': self.name_change,
            'group_uuid':  self.group,
            'group_name':  self.name_return,
            'old_name':    False if not self.name_change else self.name_old
        })

class Group_Create(RequestHandler):
    """
    API class designed to handle the creation of groups.
    """
    def launch(self):
        """
        Worker method that handles the creation of the group.
        """
            
        # Make sure the group doesn't exist
        LENSE.REQUEST.ensure(LENSE.GROUP.exists(LENSE.REQUEST.data['name']),
            value = False,
            error = 'Cannot create group, name {0} already exists'.format(LENSE.REQUEST.data['name']),
            code  = 400)
        
        # Default group UUID
        group_uuid = str(uuid4())
        
        # If manually specifying a UUID
        if LENSE.REQUEST.data.get('uuid', False):
            LENSE.REQUEST.ensure(LENSE.GROUP.exists(LENSE.REQUEST.data['uuid']),
                value = False,
                error = 'Cannot create group, UUID {0} already exists'.format(LENSE.REQUEST.data['name']),
                code  = 400)
            
            # Set the manual UUID
            group_uuid = LENSE.REQUEST.data['uuid']
            
        # Group attributes
        attrs = {
            'uuid': group_uuid,
            'name': LENSE.REQUEST.data['name'],
            'desc': LENSE.REQUEST.data['desc'],
            'protected': LENSE.REQUEST.data.get('protected', False)
        }
            
        # Create the group
        LENSE.REQUEST.ensure(LENSE.GROUP.create(**attrs),
            error = 'Failed to create group',
            log   = 'Created group {0}'.format(attrs['uuid']),
            code  = 500)
        
        # Return the response
        return valid('Successfully created group', attrs)

class Group_Get(RequestHandler):
    """
    API class designed to retrieve the details of a single group, or a list of all group
    details.
    """
    def launch(self):
        """
        Worker method for retrieving group details.
        """
        target = LENSE.REQUEST.data.get('uuid', None)
        
        # Retrieving all groups
        if not target:
            return valid(LENSE.OBJECTS.GROUP.get())
        
        # Make sure the target group exists
        group = LENSE.REQUEST.ensure(LENSE.GROUP.get(target),
            error = 'Could not locate group object {0}'.format(target),
            debug = 'Group object {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the group details
        return valid(group)
            