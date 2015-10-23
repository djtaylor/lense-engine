import importlib

# Django Libraries
from django.db import models

class DBGatewayACLAccessGlobal(models.Model):
    """
    Main database model for global ACL keys. These are ACL keys which are not
    attached to a specific object or limited to a specific group type.
    """
    acl        = models.ForeignKey('gateway.DBGatewayACLKeys', to_field='uuid', db_column='acl')
    utility    = models.ForeignKey('gateway.DBGatewayUtilities', to_field='uuid', db_column='utility')
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_access_global'

class DBGatewayACLAccessObject(models.Model):
    """
    Main database model for object ACL keys. These are ACL keys which are used
    for defining granular permissions for objects, such as hosts or formulas.
    """
    acl        = models.ForeignKey('gateway.DBGatewayACLKeys', to_field='uuid', db_column='acl')
    utility    = models.ForeignKey('gateway.DBGatewayUtilities', to_field='uuid', db_column='utility')
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_access_object'

class DBGatewayUtilities(models.Model):
    """
    Main database model for storing API utility details.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    name       = models.CharField(max_length=128, unique=True)
    path       = models.CharField(max_length=128)
    desc       = models.CharField(max_length=256)
    method     = models.CharField(max_length=6)
    mod        = models.CharField(max_length=128)
    cls        = models.CharField(max_length=64, unique=True)
    utils      = models.TextField()
    rmap       = models.TextField()
    object     = models.CharField(max_length=64, null=True, blank=True)
    object_key = models.CharField(max_length=32, null=True, blank=True)
    protected  = models.NullBooleanField()
    enabled    = models.BooleanField()
    allow_anon = models.NullBooleanField()
    locked     = models.NullBooleanField()
    locked_by  = models.CharField(max_length=64, null=True, blank=True)
    
    # Custom table metadata
    class Meta:
        db_table = 'utilities'
     
class DBGatewayACLObjectsQuerySet(models.query.QuerySet):
    """
    Custom queryset manager for the DBGatewayACLObjects model. This allows customization of the returned
    QuerySet when extracting host details from the database.
    """
    def __init__(self, *args, **kwargs):
        super(DBGatewayACLObjectsQuerySet, self).__init__(*args, **kwargs)
        
        # Detailed object list
        self._detailed = False
        
    def _extract(self, acl_object):
        """
        Extract object details.
        """
           
        # If not extracting object details
        if not self._detailed:
            return acl_object
            
        # Get an instance of the object class
        obj_mod   = importlib.import_module(acl_object['obj_mod'])
        obj_class = getattr(obj_mod, acl_object['obj_cls'])
        obj_key   = acl_object['obj_key']
        
        # Define the detailed objects container
        acl_object['objects'] = []
        for obj_details in list(obj_class.objects.all().values()):
                
            # API user objects
            if acl_object['type'] == 'user':
                acl_object['objects'].append({
                    'id':    obj_details[obj_key],
                    'name':  obj_details['username'],
                    'label': obj_details['email']              
                })
                
            # API group objects
            if acl_object['type'] == 'group':
                acl_object['objects'].append({
                    'id':    obj_details[obj_key],
                    'name':  obj_details['name'],
                    'label': obj_details['desc']            
                })
        
            # Utility objects
            if acl_object['type'] == 'utility':
                acl_object['objects'].append({
                    'id':    obj_details[obj_key],
                    'path':  obj_details['path'],
                    'label': '{0}:{1}'.format(obj_details['method'], obj_details['path'])
                })
        
        # Return the detailed ACL object
        return acl_object
        
    def values(self, detailed=False, *fields):
        """
        Wrapper for the default values() method.
        """
        
        # Set the detailed results flag
        self._detailed = detailed
        
        # Store the initial results
        _r = super(DBGatewayACLObjectsQuerySet, self).values(*fields)
        
        # ACL return object
        _a = []
        
        # Process each ACL object definition
        for acl_object in _r:
            _a.append(self._extract(acl_object))
        
        # Return the constructed ACL results
        return _a
        
class DBGatewayACLObjectsManager(models.Manager):
    """
    Custom objects manager for the DBGatewayACLObjects model. Acts as a link between the main DBGatewayACLObjects
    model and the custom DBGatewayACLObjectsQuerySet model.
    """
    def __init__(self, *args, **kwargs):
        super(DBGatewayACLObjectsManager, self).__init__()
    
    def get_queryset(self, *args, **kwargs):
        """
        Wrapper method for the internal get_queryset() method.
        """
        return DBGatewayACLObjectsQuerySet(model=self.model)

class DBGatewayACLObjects(models.Model):
    """
    Main database model for storing ACL object types.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    type       = models.CharField(max_length=36, unique=True)
    name       = models.CharField(max_length=36)
    acl_mod    = models.CharField(max_length=128)
    acl_cls    = models.CharField(max_length=64, unique=True)
    acl_key    = models.CharField(max_length=36)
    obj_mod    = models.CharField(max_length=128)
    obj_cls    = models.CharField(max_length=64)
    obj_key    = models.CharField(max_length=36)
    def_acl    = models.ForeignKey('gateway.DBGatewayACLKeys', to_field='uuid', db_column='def_acl', null=True, blank=True, on_delete=models.SET_NULL)

    # Custom objects manager
    objects    = DBGatewayACLObjectsManager()

    # Custom table metadata
    class Meta:
        db_table = 'acl_objects'

class DBGatewayACLKeysQuerySet(models.query.QuerySet):
    """
    Custom queryset manager for the DBHostManager model. This allows customization of the returned
    QuerySet when extracting host details from the database.
    """
    def __init__(self, *args, **kwargs):
        super(DBGatewayACLKeysQuerySet, self).__init__(*args, **kwargs)
        
        # ACL object types / utilities
        self.obj_types = self._get_objects()
        self.utilities = {x['uuid']: x for x in list(DBGatewayUtilities.objects.all().values())}
        
    def _get_objects(self):
        """
        Construct ACL object types and definitions.
        """
        
        # Query all ACL object types
        acl_objects = list(DBGatewayACLObjects.objects.all().values())
        
        # Construct and return the definition
        return {
            'types':   [x['type'] for x in acl_objects],
            'details': {x['type']: x for x in acl_objects},
        }
        
    def _extract_utilities(self, utilities):
        """
        Extract utility information from an ACL utility assignment.
        """
        
        # ACL utlities return object
        utilities_obj = []
        
        # Object type
        obj_type      = None
        
        # Construct the ACL utilities object
        for util in utilities:
            util_uuid = util['utility_id']
            utilities_obj.append({
                'uuid':   self.utilities[util_uuid]['uuid'],
                'path':   self.utilities[util_uuid]['path'],
                'desc':   self.utilities[util_uuid]['desc'],
                'method': self.utilities[util_uuid]['method'],
                'object': self.utilities[util_uuid]['object']
            })
            
            # If the object type is defined
            obj_type = obj_type if not self.utilities[util_uuid]['object'] else self.utilities[util_uuid]['object']
            
        # Return the ACL utilities object and object type
        return utilities_obj, obj_type
        
    def _extract(self, acl):
        """
        Extract and construct each ACL definition.
        """
        
        # Extract all utility access definitions
        object_util = self._extract_utilities(list(DBGatewayACLAccessObject.objects.filter(acl=acl['uuid']).values()))
        global_util = self._extract_utilities(list(DBGatewayACLAccessGlobal.objects.filter(acl=acl['uuid']).values()))
        
        # Contstruct the utilities for each ACL access type
        acl['utilities'] = {
            'object': {
                'type': object_util[1],
                'list': object_util[0]
            },
            'global': {
                'type': global_util[1],
                'list': global_util[0]
            }          
        }
        
        # Return the constructed ACL object
        return acl
        
    def values(self, *fields):
        """
        Wrapper for the default values() method.
        """
        
        # Store the initial results
        _r = super(DBGatewayACLKeysQuerySet, self).values(*fields)
        
        # ACL return object
        _a = []
        
        # Process each ACL definition
        for acl in _r:
            _a.append(self._extract(acl))
        
        # Return the constructed ACL results
        return _a

class DBGatewayACLKeysManager(models.Manager):
    """
    Custom objects manager for the DBGatewayACLKeys model. Acts as a link between the main DBGatewayACLKeys
    model and the custom DBGatewayACLKeysQuerySet model.
    """
    def __init__(self, *args, **kwargs):
        super(DBGatewayACLKeysManager, self).__init__()
    
    def get_queryset(self, *args, **kwargs):
        """
        Wrapper method for the internal get_queryset() method.
        """
        return DBGatewayACLKeysQuerySet(model=self.model)

class DBGatewayACLKeys(models.Model):
    """ 
    Main database model for storing ACL keys and details. Each ACL can handle
    authorization for any number of utilities.
    """
    uuid        = models.CharField(max_length=36, unique=True)
    name        = models.CharField(max_length=128, unique=True)
    desc        = models.CharField(max_length=128)
    type_object = models.BooleanField()
    type_global = models.BooleanField()
    
    # Custom objects manager
    objects     = DBGatewayACLKeysManager()
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_keys'
    
class DBGatewayACLGroupObjectGroupPermissions(models.Model):
    """
    Main database model for storing object ACL permissions for group objects.
    """
    acl        = models.ForeignKey(DBGatewayACLKeys, to_field='uuid', db_column='acl')
    group      = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='group', related_name='group_target')
    owner      = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='owner', related_name='group_owner')
    allowed    = models.NullBooleanField()
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_group_object_group_permissions'
    
class DBGatewayACLGroupObjectUserPermissions(models.Model):
    """
    Main database model for storing object ACL permissions for group objects.
    """
    acl        = models.ForeignKey(DBGatewayACLKeys, to_field='uuid', db_column='acl')
    user       = models.ForeignKey('user.DBUser', to_field='uuid', db_column='user')
    owner      = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='owner')
    allowed    = models.NullBooleanField()
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_group_object_user_permissions'
        
class DBGatewayACLGroupObjectUtilityPermissions(models.Model):
    """
    Main database model for storing object ACL permissions for utility objects.
    """
    acl        = models.ForeignKey(DBGatewayACLKeys, to_field='uuid', db_column='acl')
    utility    = models.ForeignKey(DBGatewayUtilities, to_field='uuid', db_column='utility')
    owner      = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='owner')
    allowed    = models.NullBooleanField()
        
    # Custom table metadata
    class Meta:
        db_table = 'acl_group_object_utility_permissions'
        
class DBGatewayACLGroupGlobalPermissions(models.Model):
    """
    Main database model for storing global ACL permissions for groups.
    """
    acl        = models.ForeignKey(DBGatewayACLKeys, to_field='uuid', db_column='acl')
    owner      = models.ForeignKey('group.DBGroupDetails', to_field='uuid', db_column='owner')
    allowed    = models.NullBooleanField()
    
    # Custom table metadata
    class Meta:
        db_table = 'acl_group_global_permissions'
