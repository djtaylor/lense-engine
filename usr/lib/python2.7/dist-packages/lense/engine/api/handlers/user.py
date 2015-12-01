import re

# Lense Libraries
from lense.common.vars import USERS
from lense.common.http import HTTP_GET
from lense.engine.api.handlers import RequestHandler
from lense.common.utils import valid, invalid, rstring
from lense.common.objects.user.models import APIUser, APIUserKeys

class User_Delete(RequestHandler):
    """
    API class used to handle deleting a user account.
    """
    def __init__(self, parent):
        self.api  = parent
        
        # Target user
        self.user = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method for deleting a user account.
        """
        
        # Construct a list of authorized users
        auth_users = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)
        
        # If the user does not exist or access is denied
        if not self.user in auth_users.ids:
            return invalid('Cannot delete user "{0}", not found or access denied'.format(self.user))
        LENSE.API.LOG.info('Deleting user account "{0}"'.format(self.user))
        
        # Cannot delete default administrator
        if self.user == USERS.ADMIN.UUID:
            return invalid('Cannot delete the default administrator account')

        # Delete the user account
        APIUser.objects.filter(username=self.user).delete()

        # Return the response
        return valid('Successfully deleted user account', {
            'username': self.user
        })

class User_Enable(RequestHandler):
    """
    API class used to handle enabling a user account.
    """
    def __init__(self, parent):
        self.api = parent

        # Target user
        self.user = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method used to handle enabling a user account.
        """
        
        # Construct a list of authorized users
        auth_users = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)
        
        # If the user does not exist or access is denied
        if not self.user in auth_users.ids:
            return invalid('Cannot enable user "{0}", not found or access denied'.format(self.user))
        LENSE.API.LOG.info('Enabling user account "{0}"'.format(self.user))

        # Cannot enable/disable default administrator
        if self.user == USERS.ADMIN.UUID:
            return invalid('Cannot enable/disable the default administrator account')

        # Get the user object and disable the account
        user_obj = APIUser.objects.get(username=self.user)
        user_obj.is_active = True
        user_obj.save()
        
        # Return the response
        return valid('Successfully enabled user account', {
            'username': self.user
        })

class User_Disable(RequestHandler):
    """
    API class used to handle disabling a user account.
    """
    def __init__(self, parent):
        self.api = parent

        # Target user
        self.user = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method used to handle disabling a user account.
        """
        
        # Construct a list of authorized users
        auth_users = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)
        
        # If the user does not exist or access is denied
        if not self.user in auth_users.ids:
            return invalid('Cannot disable user "{0}", not found or access denied'.format(self.user))
        LENSE.API.LOG.info('Disabling user account "{0}"'.format(self.user))

        # Cannot enable/disable default administrator
        if self.user == USERS.ADMIN.UUID:
            return invalid('Cannot enable/disable the default administrator account')

        # Get the user object and disable the account
        user_obj = APIUser.objects.get(username=self.user)
        user_obj.is_active = False
        user_obj.save()
        
        # Return the response
        return valid('Successfully disabled user account', {
            'username': self.user
        })

class User_ResetPassword(RequestHandler):
    """
    API class used to handle resetting a user's password.
    """
    def __init__(self, parent):
        self.api = parent
        
        # Targer user
        self.user = self.api.acl.target_object()
        
    def launch(self):
        """
        Worker method to handle resetting a user's password.
        """
        
        # Construct a list of authorized users
        auth_users = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)
        
        # If the user does not exist or access is denied
        if not self.user in auth_users.ids:
            return invalid('Cannot reset password for user "{0}", not found or access denied'.format(self.user))
        LENSE.API.LOG.info('Resetting password for user "{0}"]'.format(self.user))
        
        # Generate a new random password
        new_pw = rstring()

        # Get the user object and set the new password
        try:
            user_obj = APIUser.objects.get(username=self.user)
            user_obj.set_password(new_pw)
            user_obj.save()
            LENSE.API.LOG.info('Successfully reset password for user "{0}"'.format(self.user))
            
        # Critical error when resetting user password
        except Exception as e:
            return invalid('Failed to reset password for user "{0}": {1}'.format(self.user, str(e)))
        
        # Send the email
        try:
            
            # Email properties
            email_sub  = 'Lense Password Reset: {0}'.format(self.user)
            email_txt  = 'Your password has been reset. You may login with your new password: {0}'.format(new_pw)
            email_from = 'noreply@email.net'
            email_to   = [user_obj.email]
            
            # Send the email
            if self.api.email.send(email_sub, email_txt, email_from, email_to):
                LENSE.API.LOG.info('Sent email confirmation for password reset to user: {0}'.format(self.user))
            
            # Return the response
            return valid('Successfully reset user password')
        
        # Critical error when sending password reset notification
        except Exception as e:
            return invalid(LENSE.API.LOG.error('Failed to send password reset confirmation: {0}'.format(str(e))))

class User_Create(RequestHandler):
    """
    API class designed to create a new user account.
    """
    def __init__(self, parent):
        """
        Construct the UserCreate utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api  = parent

    def _validate(self):
        """
        Make sure the user request is valid.
        """

        # Make sure the user doesn't exist
        if APIUser.objects.filter(username=self.api.data['username']).count():
            return invalid(LENSE.API.LOG.error('The user account "{0}" already exists'.format(self.api.data['username'])))

        # Password RegEx Tester:
        # - At least 8 characters
        # - At least 1 lower case letter
        # - At least 1 upper case letter
        # - At least 1 number
        # - At least 1 special character
        pw_regex = re.compile(r'^\S*(?=\S{8,})(?=\S*[a-z])(?=\S*[A-Z])(?=\S*[\d])(?=\S*[\W])\S*$')
        if not pw_regex.match(self.api.data['password']):
            return invalid(LENSE.API.LOG.error('Password is too weak. Must be at least 8 characters and contain - upper/lower case letters, numbers, and special characters'))
        return valid()

    def launch(self):
        """
        Worker method used to handle creation of a new user account.
        """
        
        # Validate the user creation request
        req_status = self._validate()
        if not req_status['valid']:
            return req_status
        
        # Try to create the new user account
        try:
            
            # Generate a random password
            password = rstring()
            
            # If manually setting the password
            if ('password' in self.api.data):
                
                # Must confirm the password
                if not ('password_confirm' in self.api.data):
                    return invalid('Missing "password_confirm" request parameter')
                
                # Passwords don't match
                if not (self.api.data['password'] == self.api.data['password_confirm']):
                    return invalid('Request parameters "password" and "password_confirm" do not match')
                
                # Set the password
                password = self.api.data['password']
            
            # Check if specifying a manual user UUID
            if self.api.data.get('uuid', False):
                if APIUser.objects.filter(uuid=self.api.data['uuid']).count():
                    return invalid(LENSE.API.LOG.error('Cannot create user with duplicate UUID: {0}'.format(self.api.data['uuid'])))
                
            # Create the user account
            new_user = APIUser.objects.create_user(
                uuid         = self.api.data.get('uuid', None),
                group        = self.api.data['group'],
                username     = self.api.data['username'],
                email        = self.api.data['email'],
                password     = self.api.data['password'],
            )
                
            # Save the user account details
            new_user.save()
            LENSE.API.LOG.info('Created user account "{0}"'.format((self.api.data['username'])))
            
            # Send the account creation email
            try:
                
                # Email properties
                email_sub  = 'Lense New Account: {0}'.format(new_user.username)
                email_txt  = 'Your account has been created. You may login with your password: {0}'.format(password)
                email_from = 'noreply@email.net'
                email_to   = [new_user.email]
                
                # Send the email
                if self.api.email.send(email_sub, email_txt, email_from, email_to):
                    LENSE.API.LOG.info('Sent email confirmation for new account "{0}" to "{1}"'.format(new_user.username, new_user.email))
                
                    # Return valid
                    return valid('Successfully sent account creation confirmation')
            
            # Critical error when sending email confirmation, continue but log exception
            except Exception as e:
                LENSE.API.LOG.exception('Failed to send account creation confirmation: {0}'.format(str(e)))
            
        # Something failed during creation
        except Exception as e:
            return invalid(LENSE.API.LOG.exception('Failed to create user account "{0}": {1}'.format(self.api.data['username'], str(e))))
        
        # Get the new user's API key
        api_key = APIUserKeys.objects.filter(user=new_user.uuid).values()[0]['api_key']
        
        # Return the response
        return valid('Successfully created user account', {
            'uuid':       new_user.uuid,
            'username':   new_user.username,
            'first_name': new_user.first_name,
            'last_name':  new_user.last_name,
            'email':      new_user.email,
            'api_key':    api_key
        })

class User_Get(RequestHandler):
    """
    API class designed to retrieve the details of a single user, or a list of all user
    details.
    """
    def __init__(self, parent):
        """
        Construct the UserGet utility
        
        :param parent: The APIBase
        :type parent: APIBase
        """
        self.api  = parent
        
        # Target user
        self.user = self.api.acl.target_object()
            
    def launch(self):
        """
        Worker method that does the work of retrieving user details.
        
        :rtype: valid|invalid
        """
        
        # Construct a list of authorized user objects
        auth_users = self.api.acl.authorized_objects('user', path='user', method=HTTP_GET)
        
        # If retrieving a specific user
        if self.user:
            
            # If the user does not exist or access is denied
            if not self.user in auth_users.ids:
                return invalid('User "{0}" does not exist or access denied'.format(self.user))
            
            # Return the user details
            return valid(auth_users.extract(self.user))
            
        # If retrieving all users
        else:
            return valid(auth_users.details)