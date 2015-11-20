import os

# Lense Libraries
from lense.commomn import LenseCommon
from lense.common.vars import DB_ENCRYPT_DIR

# Lense Common
LENSE            = LenseCommon('ENGINE')

# Project base directory
BASE_DIR         = os.path.dirname(os.path.dirname(__file__))

# Debug mode
DEBUG            = True

# Hosts allowed to use the API
ALLOWED_HOSTS    = []

# Secret key
SECRET_KEY       = LENSE.CONF.engine.secret

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
API_TEMPLATES    = '{0}/api'.format(LENSE.PROJECT.TEMPLATES)

# Template directories
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ LENSE.PROJECT.TEMPLATES ],
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
EMAIL_HOST       = LENSE.CONF.email.smtp_host

# Database encryption keys
ENCRYPTED_FIELDS_KEYDIR = DB_ENCRYPT_DIR

# Database connections
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     LENSE.CONF.db.name,
        'USER':     LENSE.CONF.db.user,
        'PASSWORD': LENSE.CONF.db.password,
        'HOST':     LENSE.CONF.db.host,
        'PORT':     LENSE.CONF.db.port
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
    'lense.common.objects.acl',
    'lense.common.objects.group',
    'lense.common.objects.user',
    'lense.common.objects.utility',
    'lense.common.objects.stats'
)

# Django middleware classes
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)