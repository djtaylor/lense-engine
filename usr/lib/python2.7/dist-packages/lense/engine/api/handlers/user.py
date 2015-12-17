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
            debug = 'Launching {0} for handler object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.get(uuid=target), 
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

        # Return the response
        return self.valid('Successfully deleted user account', {
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
            debug = 'Launching {0} for user object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.get(uuid=target), 
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
        self.ensure(LENSE.OBJECTS.USER.update(target, {
            'is_active': True
        }), error = 'Failed to enable user account {0}'.format(target),
            log   = 'Enabled user account {0}'.format(target),
            code  = 500)
        
        # Return the response
        return self.valid('Successfully enabled user account', {
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
            debug = 'Launching {0} for user object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.get(uuid=target), 
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
        self.ensure(LENSE.OBJECTS.USER.update(target, {
            'is_active': False
        }), error = 'Failed to disable user account {0}'.format(target),
            log   = 'Disabled user account {0}'.format(target),
            code  = 500)
        
        # Return the response
        return self.valid('Successfully disable user account', {
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
            debug = 'Launching {0} for user object {1}'.format(__name__, LENSE.REQUEST.data['uuid']))
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Generate a new random password
        new_passwd = rstring()

        # Update the user password
        self.ensure(user.set_password(new_passwd),
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
        return self.valid('Successfully reset user password')
    
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
            error = 'User {0} already exists'.format(username),
            code  = 400)
        
        # If setting a user supplied password
        if self.get_data('password', None):
            
            # Make sure the password meets strength requirements if specifying
            self.ensure(LENSE.AUTH.check_pw_strength(passwd),
                error = 'Password does not meet strength requirements',
                code  = 400)
            
            # Make sure confirmation password matches
            self.ensure(passwd, 
                value = passwd_c,
                error = 'Confirmation password does not match',
                code  = 400)
            
        # If setting a user supplied UUID
        if self.get_data('uuid', False):
            self.ensure(LENSE.OBJECTS.USER.exists(uuid=LENSE.REQUEST.data['uuid']),
                value = False,
                error = 'Cannot create user with duplicate UUID: {0}'.format(LENSE.REQUEST.data['uuid']),
                code  = 400)
        
        # Mape new user attributes
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
            error = 'Failed to create user account',
            log   = 'Created user account',
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
        
        # Get the new users' API key
        api_key = LENSE.USER.key(user.uuid)
        
        # OK
        return self.valid('Successfully created user account', {
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
            return LENSE.OBJECTS.USER.get()
        
        # Look for the user
        user = self.ensure(LENSE.OBJECTS.USER.get(uuid=target), 
            isnot = None, 
            error = 'Could not find user: {0}'.format(target),
            debug = 'User {0} exists, retrieved object'.format(target),
            code  = 404)
        
        # Return the user details
        return self.valid(user)