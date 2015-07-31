from uuid import uuid4

# Django Libraries
from django.db import models
from django.utils import timezone
from django.core import validators
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# Lense Libraries
from lense.common.vars import G_ADMIN, G_USER, G_DEFAULT
from lense.engine.api.app.group.models import DBGroupMembers, DBGroupDetails

class DBUserAPIKeys(models.Model):
    """
    Main database model for storing user API keys.
    """
    
    # User API key table columns
    user    = models.ForeignKey('user.DBUser', to_field='uuid', db_column='user')
    api_key = models.CharField(max_length=64, unique=True)
    
    # Custom model metadata
    class Meta:
        db_table = 'api_user_keys'
        
class DBUserAPITokens(models.Model):
    """
    Main database model for storing user API tokens.
    """
    
    # User API token table columns
    user    = models.ForeignKey('user.DBUser', to_field='uuid', db_column='user')
    token   = models.CharField(max_length=255, unique=True)
    expires = models.DateTimeField()
    
    # Custom model metadata
    class Meta:
        db_table = 'api_user_tokens'

class DBUserQuerySet(models.query.QuerySet):
    """
    Custom query set for the user model.
    """
    
    # Timestamp format / timefield keys
    timestamp  = '%Y-%m-%d %H:%M:%S'
    timefields = ['date_joined', 'last_login']
    
    def __init__(self, *args, **kwargs):
        super(DBUserQuerySet, self).__init__(*args, **kwargs)

    def _is_admin(self, user):
        """
        Check if the user is a member of the administrator group.
        """
        groups = self._get_groups(user)
        for group in groups:
            if group['uuid'] == G_ADMIN:
                return True
        return False

    def _get_groups(self, user):
        """
        Retrieve a list of group membership.
        """
        membership = []
        for g in DBGroupMembers.objects.filter(member=user).values():
            gd = DBGroupDetails.objects.filter(uuid=g['group_id']).values()[0]
            membership.append({
                'uuid': gd['uuid'],
                'name': gd['name'],
                'desc': gd['desc']
            })
        return membership

    def values(self, *fields):
        """
        Wrapper for the default values() method.
        """
        
        # Store the initial results
        _u = super(DBUserQuerySet, self).values(*fields)
        
        # Process each user object definition
        for user in _u:
            
            # Parse any time fields
            for timefield in self.timefields:
                if timefield in user:
                    user[timefield] = user[timefield].strftime(self.timestamp)
            
            # Remove the password
            del user['password']
            
            # Get user groups and administrator status
            user.update({
                'groups': self._get_groups(user['uuid']),
                'is_admin': self._is_admin(user['uuid'])
            })
        
        # Return the constructed user results
        return _u

class DBUserManager(BaseUserManager):
    """
    Custom user manager for the custom user model.
    """
    def get_queryset(self, *args, **kwargs):
        """
        Wrapper method for the internal get_queryset() method.
        """
        return DBUserQuerySet(model=self.model)
        
    def get_or_create(self, *args, **kwargs):
        """
        Get or create a new user object.
        """
        
        # Get the user queryset
        queryset = self.get_queryset()
        
        # If the user exists
        if queryset.filter(username=kwargs['username']).count():
            return queryset.get(username=kwargs['username']), False
        
        # User doesn't exist yet
        user = self.create_user(*args, **kwargs)
        
        # Return the created user
        return user, True
        
    def create_user(self, group=G_DEFAULT, uuid=None, **attrs):
        """
        Create a new user account.
        """
        
        # Required attributes
        for k in ['username', 'email', 'password']:
            if not k in attrs:
                raise Exception('Missing required attribute [%s], failed to create user' % k)
        
        # Import the API keys module
        from lense.engine.api.auth.key import APIKey
        
        # Get the current timestamp
        now = timezone.now()
        
        # Generate a unique ID for the user
        user_uuid = str(uuid4())
        
        # If manually specifying a UUID
        if uuid:
            user_uuid = uuid
        
        # Update the user creation attributes
        attrs.update({
            'uuid':        user_uuid,
            'is_active':   True,
            'last_login':  now,
            'date_joined': now
        })
        # Create a new user object
        user = self.model(**attrs)
        
        # Set the password and and save
        user.set_password(attrs['password'])
        user.save(using=self._db)
        
        # Get the group object
        group = DBGroupDetails.objects.get(uuid=group)
        
        # Add the user to the group
        group.members_set(user)
        
        # Generate an API key for the user
        api_key = DBUserAPIKeys(
            user    = user,
            api_key = APIKey().create()
        ).save()
        
        # Return the user object
        return user

class DBUser(AbstractBaseUser):
    """
    Main database model for user accounts.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    username   = models.CharField(_('username'), 
        max_length = 30, 
        unique     = True,
        help_text  = _('Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators = [
            validators.RegexValidator(r'^[\w.@+-]+$',
            _('Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.'), 
            'invalid'),
        ],
        error_messages = {
            'unique': _("A user with that username already exists."),
        })
    
    # First / last name / email
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name  = models.CharField(_('last name'), max_length=30, blank=True)
    email      = models.EmailField(_('email address'), blank=True)
    
    # Is the account active
    is_active = models.BooleanField(_('active'), 
        default   = True,
        help_text = _('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    )
    
    # Date joined
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    # Is the user authenticated from LDAP
    from_ldap = models.BooleanField(_('LDAP User'), editable=False, default=False)

    # User objects manager
    objects = DBUserManager()

    # Username field and required fields
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    # Model metadata
    class Meta:
        db_table = 'api_users'
        verbose_name = _('user')
        verbose_name_plural = _('users')