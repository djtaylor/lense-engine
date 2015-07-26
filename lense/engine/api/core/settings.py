import os

# Lense Libraries
import lense.common.config as config
from lense.common.vars import L_BASE

# Configuration
CONFIG           = config.parse()

# Project base directory
BASE_DIR         = os.path.dirname(os.path.dirname(__file__))

# Debug mode
DEBUG            = True
TEMPLATE_DEBUG   = True

# Hosts allowed to use the API
ALLOWED_HOSTS    = []

# Secret key
SECRET_KEY       = CONFIG.server.secret

# Internationalization settings
LANGUAGE_CODE    = 'en-us'
TIME_ZONE        = 'UTC'
USE_I18N         = True
USE_L10N         = True
USE_TZ           = True

# API token lifetime in hours
API_TOKEN_LIFE   = 1

# Static files
STATIC_URL       = '/static/'

# URL processor
ROOT_URLCONF     = 'lense.engine.api.core.urls'

# API WSGI application
WSGI_APPLICATION = 'lense.engine.api.core.wsgi.application'

# API request templates
API_TEMPLATES    = '%s/python/lense/engine/templates/api' % L_BASE

# Template directories
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
           '%s/python/lense/engine/templates' % L_BASE
        ],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# SMTP backend
EMAIL_HOST       = CONFIG.email.smtp_host

# Database encryption keys
ENCRYPTED_FIELDS_KEYDIR = '%s/dbkey' % L_BASE

# Database connections
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     'lense',
        'USER':     CONFIG.db.user,
        'PASSWORD': CONFIG.db.password,
        'HOST':     CONFIG.db.host,
        'PORT':     CONFIG.db.port
    }
}

# Managed applications
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'lense.engine.api.app.gateway',
    'lense.engine.api.app.user',
    'lense.engine.api.app.group',
)

# Django middleware classes
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)