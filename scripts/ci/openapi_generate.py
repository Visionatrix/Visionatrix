# Script to create an OpenAPI.json file in the root of the repository.
# Currently, it should be run manually after making changes to the backend.

import json
import os
import builtins
from pathlib import Path

os.chdir(Path(__file__).parent.parent.parent)  # set current directory to the repository root

from visionatrix.backend import APP  # noqa
from visionatrix import _version  # noqa


openapi_schema = APP.openapi()
openapi_schema["info"]["title"] = "visionatrix"
openapi_schema["info"]["version"] = _version.__version__

with builtins.open("openapi.json", "w", encoding="UTF-8") as f:
    json.dump(openapi_schema, f, indent=2)

print("OpenAPI schema has been generated and saved to openapi.json")
