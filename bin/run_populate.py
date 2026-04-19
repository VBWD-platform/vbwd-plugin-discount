#!/usr/bin/env python
"""Run discount populate_db inside the running Flask app context."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from vbwd.app import create_app

app = create_app()
with app.app_context():
    from plugins.discount.populate_db import populate
    populate(app)
    print("Discount populate complete.")
