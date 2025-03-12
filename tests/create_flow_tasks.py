import os
import sys
import json
import requests


def load_openapi_schema(schema_name, openapi_json):
    """
    Given a schema reference like "#/components/schemas/TaskRun_flux1_dev_inpaint",
    return the actual schema dict from openapi_flows.json
    """
    if not schema_name.startswith("#/components/schemas/"):
        raise ValueError(f"Unsupported schema reference: {schema_name}")
    name = schema_name.split("/")[-1]  # e.g. "TaskRun_flux1_dev_inpaint"
    return openapi_json["components"]["schemas"].get(name, {})


def get_test_value_for_property(prop_name, prop_schema):
    """
    Given a single property schema, return the data (string, file, integer, etc.)
    to pass in the multipart form.
    """
    # 1) If it's an image field (anyOf with format "binary"), attach the local file.
    # 2) If it's an enum, use its 'default' if given, else first from 'enum'.
    # 3) If it's an integer or number, use the default if any, else a minimum or a fallback.
    # 4) Otherwise string fallback => "test".

    # Check for "anyOf" with contentMediaType = "image/*"
    if "anyOf" in prop_schema:
        for any_schema in prop_schema["anyOf"]:
            if any_schema.get("format") == "binary":
                # We found a file property
                filename = "tests/source-cube_rm_background.png"
                return ("source-cube_rm_background.png", open(filename, "rb"), "image/png")

    # Check for an enum
    if "enum" in prop_schema:
        if "default" in prop_schema:
            return str(prop_schema["default"])  # just use default
        # else pick first from enum
        return str(prop_schema["enum"][0])

    # If it's a number or integer
    if prop_schema.get("type") in ["number", "integer"]:
        # If a default is defined, use it
        if "default" in prop_schema:
            return str(prop_schema["default"])
        # else if there is a minimum or maximum, we can try picking that
        if "minimum" in prop_schema:
            return str(prop_schema["minimum"])
        # fallback
        return "1"

    # If no special cases, return a default "test" string
    if "default" in prop_schema:
        # Use the default if present
        return str(prop_schema["default"])

    return "test"


def main():
    openapi_file = "openapi-flows.json"
    server_url = os.environ.get("TEST_VIX_URL", "http://localhost:8288")
    errors = []

    if not os.path.exists(openapi_file):
        print(f"Cannot find {openapi_file}")
        sys.exit(1)

    with open(openapi_file, "r", encoding="utf-8") as f:
        openapi_json = json.load(f)

    # Loop all paths in openapi
    for path, methods_info in openapi_json.get("paths", {}).items():
        # We only care about the "PUT" in "tasks/create/..."
        put_info = methods_info.get("put")
        if not put_info:
            continue
        if "/vapi/tasks/create/" not in path:
            continue

        print(f"\n--- Testing flow creation for {path} ---")

        # The requestBody => content => multipart/form-data => schema => $ref
        req_body = put_info.get("requestBody", {})
        content = req_body.get("content", {}).get("multipart/form-data", {})
        schema_ref = content.get("schema", {}).get("$ref")
        if not schema_ref:
            print(f"  No schema ref for {path}? Skipping.")
            continue

        flow_schema = load_openapi_schema(schema_ref, openapi_json)
        required_props = flow_schema.get("required", [])
        props = flow_schema.get("properties", {})

        # Build a dictionary for data & files
        # We'll separate them into `fields_data` for text fields
        # and `files_data` for file fields, then combine them for requests
        fields_data = {}
        files_data = {}

        for prop_name in required_props:
            prop_schema = props.get(prop_name, {})
            val = get_test_value_for_property(prop_name, prop_schema)

            # If val is a tuple => we treat it as a file
            if isinstance(val, tuple):
                # This is the (filename, filehandle, mimetype) for requests
                files_data[prop_name] = val
            else:
                fields_data[prop_name] = val

        # Make the request
        # According to requests docs:
        #   requests.put(..., data=fields_data, files=files_data) => multipart/form-data
        full_url = f"{server_url}{path}"
        print(f"  Sending PUT to {full_url}")
        try:
            resp = requests.put(full_url, data=fields_data, files=files_data, timeout=15, auth=("user", "user"))
        except Exception as ex:
            errors.append(f"{path} => EXCEPTION: {ex}")
            continue
        finally:
            # Important to close file handles if we used them
            for f_tuple in files_data.values():
                f_tuple[1].close()

        if resp.status_code != 200:
            errors.append(f"{path} => Status {resp.status_code}: {resp.text[:400]}")

    if errors:
        print("\nERRORS detected in flow creation test:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    else:
        print("\nAll flows creation tests responded with 200. Success!")


if __name__ == "__main__":
    main()
