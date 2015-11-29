import os
from lense.common import init_project

# Load Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lense.engine.api.core.settings")

# Initialize the project
init_project('ENGINE')

# Start the API WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()