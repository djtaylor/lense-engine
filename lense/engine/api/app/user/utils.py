import re

# Lense Libraries
from lense.common.utils import valid, invalid, rstring
from lense.common.vars import G_ADMIN, U_ADMIN
from lense.common.http import HTTP_GET
from lense.engine.api.app.user.models import DBUser, DBUserAPIKeys
from lense.engine.api.app.group.models import DBGroupDetails

class UserDelete:
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
            return invalid('Cannot delete user [%s], not found or access denied' % self.user)
        self.api.log.info('Deleting user account [%s]' % self.user)
        
        # Cannot delete default administrator
        if self.user == U_ADMIN:
            return invalid('Cannot delete the default administrator account')

        # Delete the user account
        DBUser.objects.filter(username=self.user).delete()

        # Return the response
        return valid('Successfully deleted user account', {
            'username': self.user
        })

class UserEnable:
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
            return invalid('Cannot enable user [%s], not found or access denied' % self.user)
        self.api.log.info('Enabling user account [%s]' % self.user)

        # Cannot enable/disable default administrator
        if self.user == U_ADMIN:
            return invalid('Cannot enable/disable the default administrator account')

        # Get the user object and disable the account
        user_obj = DBUser.objects.get(username=self.user)
        user_obj.is_active = True
        user_obj.save()
        
        # Return the response
        return valid('Successfully enabled user account', {
            'username': self.user
        })

class UserDisable:
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
            return invalid('Cannot disable user [%s], not found or access denied' % self.user)
        self.api.log.info('Disabling user account [%s]' % self.user)

        # Cannot enable/disable default administrator
        if self.user == U_ADMIN:
            return invalid('Cannot enable/disable the default administrator account')

        # Get the user object and disable the account
        user_obj = DBUser.objects.get(username=self.user)
        user_obj.is_active = False
        user_obj.save()
        
        # Return the response
        return valid('Successfully disabled user account', {
            'username': self.user
        })

class UserResetPassword:
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
            return invalid('Cannot reset password for user [%s], not found or access denied' % self.user)
        self.api.log.info('Resetting password for user [%s]' % self.user)
        
        # Generate a new random password
        new_pw = rstring()

        # Get the user object and set the new password
        try:
            user_obj = DBUser.objects.get(username=self.user)
            user_obj.set_password(new_pw)
            user_obj.save()
            self.api.log.info('Successfully reset password for user [%s]' % self.user)
            
        # Critical error when resetting user password
        except Exception as e:
            return invalid('Failed to reset password for user [%s]: %s' % (self.user, str(e)))
        
        # Send the email
        try:
            
            # Email properties
            email_sub  = 'CloudScape Password Reset: %s' % self.user
            email_txt  = 'Your password has been reset. You may login with your new password "%s".' % new_pw
            email_from = 'noreply@vpls.net'
            email_to   = [user_obj.email]
            
            # Send the email
            if self.api.email.send(email_sub, email_txt, email_from, email_to):
                self.api.log.info('Sent email confirmation for password reset to user [%s]' % self.user)
            
            # Return the response
            return valid('Successfully reset user password')
        
        # Critical error when sending password reset notification
        except Exception as e:
            return invalid(self.api.log.error('Failed to send password reset confirmation: %s' % str(e)))

class UserCreate:
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
        if DBUser.objects.filter(username=self.api.data['username']).count():
            return invalid(self.api.log.error('The user account [%s] already exists' % self.api.data['username']))

        # Password RegEx Tester:
        # - At least 8 characters
        # - At least 1 lower case letter
        # - At least 1 upper case letter
        # - At least 1 number
        # - At least 1 special character
        pw_regex = re.compile(r'^\S*(?=\S{8,})(?=\S*[a-z])(?=\S*[A-Z])(?=\S*[\d])(?=\S*[\W])\S*$')
        if not pw_regex.match(self.api.data['password']):
            return invalid(self.api.log.error('Password is too weak. Must be at least [8] characters and contain - upper/lower case letters, numbers, and special characters'))
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
                    return invalid('Missing [password_confirm] request parameter')
                
                # Passwords don't match
                if not (self.api.data['password'] == self.api.data['password_confirm']):
                    return invalid('Request parameters [password] and [password_confirm] do not match')
                
                # Set the password
                password = self.api.data['password']
            
            # Check if specifying a manual user UUID
            if self.api.data.get('uuid', False):
                if DBUser.objects.filter(uuid=self.api.data['uuid']).count():
                    return invalid(self.api.log.error('Cannot create user with duplicate UUID <%s>' % self.api.data['uuid']))
                
            # Create the user account
            new_user = DBUser.objects.create_user(
                uuid         = self.api.data.get('uuid', None),
                group        = self.api.data['group'],
                username     = self.api.data['username'],
                email        = self.api.data['email'],
                password     = self.api.data['password'],
            )
                
            # Save the user account details
            new_user.save()
            self.api.log.info('Created user account [%s]' % (self.api.data['username']))
            
            # Send the account creation email
            try:
                
                # Email properties
                email_sub  = 'CloudScape New Account: %s' % new_user.username
                email_txt  = 'Your account has been created. You may login with your password "%s".' % password
                email_from = 'noreply@vpls.net'
                email_to   = [new_user.email]
                
                # Send the email
                if self.api.email.send(email_sub, email_txt, email_from, email_to):
                    self.api.log.info('Sent email confirmation for new account [%s] to [%s]' % (new_user.username, new_user.email))
                
                    # Return valid
                    return valid('Successfully sent account creation confirmation')
            
            # Critical error when sending email confirmation, continue but log exception
            except Exception as e:
                self.api.log.exception('Failed to send account creation confirmation: %s' % str(e))
            
        # Something failed during creation
        except Exception as e:
            return invalid(self.api.log.exception('Failed to create user account [%s]: %s' % (self.api.data['username'], str(e))))
        
        # Get the new user's API key
        api_key = DBUserAPIKeys.objects.filter(user=new_user.uuid).values()[0]['api_key']
        
        # Return the response
        return valid('Successfully created user account', {
            'uuid':       new_user.uuid,
            'username':   new_user.username,
            'first_name': new_user.first_name,
            'last_name':  new_user.last_name,
            'email':      new_user.email,
            'api_key':    api_key
        })

class UserGet:
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
                return invalid('User [%s] does not exist or access denied' % self.user)
            
            # Return the user details
            return valid(auth_users.extract(self.user))
            
        # If retrieving all users
        else:
            return valid(auth_users.details)