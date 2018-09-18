"""
An exemplifying Apache python WSGI to a Devicehub app.

Based in http://flask.pocoo.org/docs/0.12/deploying/mod_wsgi/

You only need to modify ``app_dir``.
"""

from pathlib import Path

import sys

app_dir = Path(__file__).parent
"""The **directory** where app.py is located. Change this accordingly."""

assert app_dir.is_dir(), 'app_dir must point to a directory: {}'.format(app_dir)
app_dir = str(app_dir.resolve())

# Load the app
# ------------
sys.path.insert(0, str(app_dir))
# noinspection PyUnresolvedReferences
from app import app as application
