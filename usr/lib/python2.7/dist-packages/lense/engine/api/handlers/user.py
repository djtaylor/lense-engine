from lense.common.vars import USERS
from lense.engine.api.handlers import RequestHandler
from lense.common.utils import rstring

ERR_NO_UUID='No user UUID found in request data'

class User_Delete(RequestHandler):
    """
    API class used to handle deleting a user account.
    """
    def launch(self):
        """
        Worker method for deleting a user account.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for handler object {1}'.format(__name__, self.get_data('uuid')))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.set(acl=True).get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Cannot delete the default administrator
        self.ensure(target,
            isnot = USERS.ADMIN.UUID,
            error = 'Cannot delete the default administrator account',
            code  = 400)
        
        # Delete the account
        self.ensure(LENSE.OBJECTS.USER.delete(uuid=target),
            error = 'Failed to delete user {0}'.format(target),
            log   = 'Deleted user account {0}'.format(target),
            code  = 500)

        # OK
        return self.ok('Deleted user account: {0}'.format(target), {
            'uuid': target
        })

class User_Enable(RequestHandler):
    """
    API class used to handle enabling a user account.
    """ 
    def launch(self):
        """
        Worker method used to handle enabling a user account.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for user object {1}'.format(__name__, self.get_data('uuid')))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.set(acl=True).get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Cannot enable/disable the default administrator
        self.ensure(target,
            isnot = USERS.ADMIN.UUID,
            error = 'Cannot enable/disable the default administrator account',
            code  = 400)
        
        # Enable the user account
        self.ensure(LENSE.OBJECTS.USER.select(**{'uuid': target}).update(uuid=target, is_active=False), 
            error = 'Failed to enable user account {0}'.format(target),
            log   = 'Enabled user account {0}'.format(target),
            code  = 500)
        
        # OK
        return self.ok('Enabled user account: {0}'.format(target), {
            'uuid': target
        })

class User_Disable(RequestHandler):
    """
    API class used to handle disabling a user account.
    """ 
    def launch(self):
        """
        Worker method used to handle disabling a user account.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for user object {1}'.format(__name__, self.get_data('uuid')))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.set(acl=True).get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Cannot enable/disable the default administrator
        self.ensure(target,
            isnot = USERS.ADMIN.UUID,
            error = 'Cannot enable/disable the default administrator account',
            code  = 400)
        
        # Disable the user account
        self.ensure(LENSE.OBJECTS.USER.select(**{'uuid': target}).update(uuid=target, is_active=False), 
            error = 'Failed to disable user account {0}'.format(target),
            log   = 'Disabled user account {0}'.format(target),
            code  = 500)
        
        # OK
        return self.ok('Disabled user account: {0}'.format(target), {
            'uuid': target
        })

class User_ResetPassword(RequestHandler):
    """
    API class used to handle resetting a user's password.
    """ 
    def launch(self):
        """
        Worker method to handle resetting a user's password.
        """
        target = self.ensure(self.get_data('uuid', None),
            isnot = None,
            error = ERR_NO_UUID,
            code  = 400,
            debug = 'Launching {0} for user object {1}'.format(__name__, self.get_data('uuid')))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.set(acl=True).get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Generate a new random password
        new_passwd = rstring()

        # Update the user password
        user.set_password(new_passwd)
        self.ensure(user.save(),
            error = 'Failed to reset user password for {0}'.format(target),
            log   = 'Reset password for user {0}'.format(target),
            code  = 500)

        # Confirmation email attributes
        email_attrs = {
            'sub':  'Lense Password Reset: {0}'.format(user.username),
            'txt':  'Your password has been reset. You may login with your new password: {0}'.format(new_passwd),
            'from': 'noreply@lense.com',
            'to':   [user.email]
        }
        
        # Send the confirmation email
        LENSE.MAIL.send(*[x[1] for x in email_attrs])
        
        # OK
        return self.ok('Reset password for user: {0}'.format(target))
    
class User_Create(RequestHandler):
    """
    API class designed to create a new user account.
    """
    def launch(self):
        """
        Worker method used to handle creation of a new user account.
        """
        username = self.get_data('username')
        passwd   = self.get_data('password', rstring())
        passwd_c = self.get_data('password_confirm', None)
        
        # Make sure the user doesn't exist
        self.ensure(LENSE.OBJECTS.USER.exists(username=username), 
            value = False,
            error = 'User "{0}" already exists'.format(username),
            debug = 'User "{0}" doesn\'t exist, OK to create'.format(username),
            code  = 400)
        
        # If setting a user supplied password
        if self.get_data('password', None):
            
            # Make sure the password meets strength requirements if specifying
            self.ensure(LENSE.AUTH.check_pw_strength(passwd),
                error = 'Password does not meet strength requirements',
                debug = 'Password strength for user "{0}" OK'.format(username),
                code  = 400)
            
            # Make sure confirmation password matches
            self.ensure(passwd, 
                value = passwd_c,
                error = 'Confirmation password does not match',
                debug = 'New user "{0}" data keys "password" and "password_confirm" match'.format(username),
                code  = 400)
            
        # If setting a user supplied UUID
        if self.get_data('uuid', False):
            self.ensure(LENSE.OBJECTS.USER.exists(uuid=self.get_data('uuid')),
                isnot = True,
                error = 'Cannot create user with duplicate UUID: {0}'.format(self.get_data('uuid')),
                code  = 400)
        
        # Map new user attributes
        attrs = LENSE.REQUEST.map_data([
            'username', 
            'email', 
            'password'                          
        ])
        
        # Set the user UUID
        if self.get_data('uuid', None):
            attrs['uuid'] = self.get_data('uuid')
        
        # Create the user account
        user = self.ensure(LENSE.OBJECTS.USER.create(**attrs),
            isnot = False,
            error = 'Failed to create user account: username={0}, email={1}'.format(attrs['username'], attrs['email']),
            log   = 'Created user account: username={0}, email={1}'.format(attrs['username'], attrs['email']),
            code  = 500)
        
        # Store the user password hash
        user.set_password(passwd)
        user.save()
        
        # Grant the user an API key
        api_key = self.ensure(LENSE.OBJECTS.USER.grant_key(user),
            isnot = False,
            error = 'Failed to grant API key to new user "{0}"'.format(user.username),
            code  = 500)
        
        # Grant the user an API token
        self.ensure(LENSE.OBJECTS.USER.grant_token(user),
            isnot = False,
            error = 'Failed to grant API token to new user "{0}"'.format(user.username),
            code  = 500)
        
        # Confirmation email attributes
        email_attrs = {
            'sub':  'Lense New Account: {0}'.format(user.username),
            'txt':  'Your account has been created. You may login with your password: {0}'.format(passwd),
            'from': 'noreply@lense.com',
            'to':   [user.email]
        }
        
        # Send the confirmation email
        LENSE.MAIL.send(*[x[1] for x in email_attrs])
        
        # OK
        return self.ok('Created user account: {0}'.format(user.uuid), {
            'uuid':       user.uuid,
            'username':   user.username,
            'first_name': user.first_name,
            'last_name':  user.last_name,
            'email':      user.email,
            'api_key':    api_key                                                          
        })

class User_Get(RequestHandler):
    """
    API class designed to retrieve the details of a single user, or a list of all user
    details.
    """
    def launch(self):
        """
        Worker method that does the work of retrieving user details.
        
        :rtype: valid|invalid
        """
        target = self.get_data('uuid', None)
        
        # Return all users
        if not target:
            return self.ok(data=LENSE.OBJECTS.USER.set(acl=True, dump=True).get())
        
        # Look for the user
        return self.ok(data=self.ensure(LENSE.OBJECTS.USER.set(acl=True, dump=True).get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404))