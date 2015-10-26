# Django Libraries
from django.db import models

class DBCallbackHandlers(models.Model):
    """
    Main database model for storing 3rd party API connectors.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    provider   = models.CharField(max_length=128, unique=True)
    
    # Custom table metadata
    class Meta:
        db_table = 'callbacks'