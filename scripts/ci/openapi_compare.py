import json
import sys
import builtins

from jsondiff import diff


def load_json(file_path):
    with builtins.open(file_path) as file:
        return json.load(file)


def remove_dynamic_fields(data):
    if isinstance(data, dict):
        if "last_seen" in data:
            del data["last_seen"]
        for value in data.values():
            remove_dynamic_fields(value)
    elif isinstance(data, list):
        for item in data:
            remove_dynamic_fields(item)


def main(generated_file: str, existing_file: str):
    generated_data = load_json(generated_file)
    existing_data = load_json(existing_file)

    remove_dynamic_fields(generated_data)
    remove_dynamic_fields(existing_data)

    differences = diff(existing_data, generated_data)

    if differences:
        print("OpenAPI specs are not up to date. Please regenerate the specs.")
        print("Differences:", differences)
        sys.exit(1)
    else:
        print("OpenAPI specs are up to date.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: compare_openapi.py <generated_file> <existing_file>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
