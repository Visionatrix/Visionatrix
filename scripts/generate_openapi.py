# Script to create an OpenAPI.json file in the root of the repository.
# Currently, it should be run manually after making changes to the backend.

import json
import os
from pathlib import Path

os.chdir(Path(__file__).parent.parent)  # set current directory to the repository root

from visionatrix.backend import APP  # noqa
from visionatrix import _version  # noqa


openapi_schema = APP.openapi()
openapi_schema["info"]["title"] = "visionatrix-client"
openapi_schema["info"]["version"] = _version.__version__

with open("openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)

print("OpenAPI schema has been generated and saved to openapi.json")
