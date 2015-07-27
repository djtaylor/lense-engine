#!/usr/bin/python
import lense.engine as lense_engine
from setuptools import setup, find_packages

# Module version / long description
version = lense_engine.__version__
long_desc = open('DESCRIPTION.rst').read()

# Run the setup
setup(
    name             = 'lense-engine',
    version          = version,
    description      = 'Lense API platform engine libraries',
    long_description = long_desc,
    author           = 'David Taylor',
    author_email     = 'djtaylor13@gmail.com',
    url              = 'http://github.com/djtaylor/lense-engine',
    license          = 'GPLv3',
    packages         = find_packages(),
    keywords         = 'lense api server platform engine',
    classifiers      = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Terminals',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Framework :: Django',
        'Framework :: Django :: 1.8'
    ],
    install_requires = [
        'Django>=1.8.3',
        'feedback>=0.1',
        'lense-common>=0.1',
        'lense-client>=0.1',
        'django_auth_ldap>=1.2.6',
        'socketIO_client>=0.6.3',
        'django_encrypted_fields>=1.1.1',
        'py3compat>=0.2',
        'MySQL-python>=1.2.3',
        'python-ldap>=2.4.10'
    ],
    entry_points     = {
        'console_scripts': [
            'lense-server = lense.common.service:cli',
        ],
    },
    include_package_data = True
)