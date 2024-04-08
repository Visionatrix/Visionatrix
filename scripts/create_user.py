"""For devs: use this script to create additional users."""

import os
from pathlib import Path

os.chdir(Path(__file__).parent.parent)

import visionatrix.database  # noqa

visionatrix.database.init_database_engine()
visionatrix.database.create_user("user", "User", "user@example.com", "user", False, False)
