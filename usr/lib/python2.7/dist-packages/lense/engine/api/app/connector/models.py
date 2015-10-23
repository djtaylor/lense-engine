# Django Libraries
from django.db import models

class DBConnectors(models.Model):
    """
    Main database model for storing 3rd party API connectors.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    name       = models.CharField(max_length=128, unique=True)
    
    # Custom table metadata
    class Meta:
        db_table = 'connectors'
        
class DBConnectorCallbacks(models.Model):
    """
    Main database model for storing callback URLs for API connectors.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    connector  = models.ForeignKey('connector.DBConnectors', to_field='uuid', db_column='connector')
    name       = models.CharField(max_length=128, unique=True)
    
    # Custom table metadata
    class Meta:
        db_table = 'connector_callbacks'