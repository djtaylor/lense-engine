# Django Libraries
from django.db import models

class DBIntegrators(models.Model):
    """
    Main database model for storing 3rd party API integrators.
    """
    uuid       = models.CharField(max_length=36, unique=True)
    name       = models.CharField(max_length=128, unique=True)
    path       = models.CharField(max_length=128)
    method     = models.CharField(max_length=6)
    imap       = models.TextField()
    
    # Custom table metadata
    class Meta:
        db_table = 'integrators'