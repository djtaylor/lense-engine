#!/usr/bin/env python
import os
import sys

# Lense API Django project management
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lense.engine.api.core.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
