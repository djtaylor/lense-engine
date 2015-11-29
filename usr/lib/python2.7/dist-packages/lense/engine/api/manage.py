#!/usr/bin/env python
from sys import argv
from os.environ import setdefault

# Lense API Django project management
if __name__ == "__main__":
    setdefault("DJANGO_SETTINGS_MODULE", "lense.engine.api.core.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(argv)
