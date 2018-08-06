#!/usr/bin/env python
from sys import argv
from os import environ

# Lense project management
if __name__ == "__main__":
    environ.setdefault("DJANGO_SETTINGS_MODULE", "lense.engine.api.core.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(argv)
