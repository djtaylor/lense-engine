# Django Libraries
from django.conf.urls import patterns, include, url

# Load the request dispatcher
urlpatterns = patterns('',
    url(r'^.*$', 'lense.engine.api.core.request.dispatch'),
)
