# Django Libraries
from django.db import models
from encrypted_fields import EncryptedTextField

class DBConnectorsOAuth2(models.Model):
    """
    Main database model for storing API OAuth2 attributes
    """
    uuid       = models.CharField(max_length=36, unique=True)
    connector  = models.ForeignKey('connector.DBConnectors', to_field='uuid', db_column='connector')
    key_file   = EncryptedTextField()
    token_url  = models.CharField(max_length=256)
    auth_url   = models.CharField(max_length=256)

    # Custom table metadata
    class Meta:
        db_table = 'connectors_oauth2'

class DBConnectors(models.Model):
    """
    Main database model for storing 3rd party API connectors.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    name       = models.CharField(max_length=128, unique=True)
    is_oauth2  = models.BooleanField()
    
    # Custom table metadata
    class Meta:
        db_table = 'connectors'