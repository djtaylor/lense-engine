# Django Libraries
from django.db import models

class DBStatsRequest(models.Model):
    """
    Main database model for storing API request stats.
    """
    path         = models.CharField(max_length=128)
    method       = models.CharField(max_length=6)
    client_ip    = models.CharField(max_length=15)
    client_user  = models.CharField(max_length=36)
    client_group = models.CharField(max_length=36)
    endpoint_ip  = models.CharField(max_length=15)
    user_agent   = models.CharField(max_length=256)
    retcode      = models.IntegerField()
    req_size     = models.IntegerField()
    rsp_size     = models.IntegerField()
    created      = models.DateTimeField(auto_now_add=True)
    
    # Custom table metadata
    class Meta:
        db_table = 'stats_requests'