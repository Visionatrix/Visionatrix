import argparse
import builtins
import importlib.resources
import json
import logging
import os
import sys
from fnmatch import fnmatchcase
from pathlib import Path

from . import comfyui, database, generate_openapi, install, options, run_vix, update
from .etc import get_higher_log_level, get_log_level
from .flows import get_not_installed_flows, get_vix_flow, install_custom_flow
from .orphan_models import process_orphan_models

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        const="DEBUG",
        nargs="?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    subparsers = parser.add_subparsers(dest="command")
    for i in [
        ("install", "Performs cleanup & initialization"),
        ("update", "Performs update to the latest version"),
        ("run", "Starts the ComfyUI and Visionatrix backends"),
        ("install-flow", "Install flow by name or from file"),
        ("create-user", "Create new user"),
        ("orphan-models", "Remove orphan models"),
        ("openapi", "Generate OpenAPI specs"),
    ]:
        subparser = subparsers.add_parser(i[0], help=i[1])
        if i[0] == "create-user":
            subparser.add_argument("--name", type=str, help="User name(ID)", required=True)
            subparser.add_argument("--password", type=str, help="User password", required=True)
            subparser.add_argument("--full_name", type=str, help="Full User Name", default="John Doe")
            subparser.add_argument("--email", type=str, help="User's email address", default="user@example.com")
            subparser.add_argument("--admin", type=bool, help="Should user be admin", default=True)
            subparser.add_argument("--disabled", type=bool, help="Should account be disabled", default=False)
            continue

        if i[0] == "orphan-models":
            subparser.add_argument(
                "--no-confirm", action="store_true", help="Do not ask for confirmation for each model"
            )
            subparser.add_argument(
                "--dry-run", action="store_true", help="Perform cleaning without actual removing models"
            )
            subparser.add_argument(
                "--include-useful-models",
                action="store_true",
                help="Include orphaned models that can be used in future flows for removal",
            )

        if i[0] == "openapi":
            subparser.add_argument(
                "--file",
                type=str,
                help="Filename to save",
                default="openapi.json",
            )
            subparser.add_argument(
                "--indentation",
                type=int,
                help="Indentation size",
                default=2,
            )
            subparser.add_argument(
                "--flows",
                type=str,
                help="Flows to include in OpenAPI specs (comma-separated list or '*')",
                default="",
            )
            subparser.add_argument(
                "--skip-not-installed",
                action="store_true",
                help="Skip flows that are not installed",
                default=True,
            )
            subparser.add_argument(
                "--exclude-base",
                action="store_true",
                help="Exclude base application endpoints from OpenAPI specs",
                default=False,
            )

        if i[0] == "install-flow":
            install_flow_group = subparser.add_mutually_exclusive_group(required=True)
            install_flow_group.add_argument(
                "--file",
                type=str,
                help="Path to `comfyui_flow.json` file or a directory containing flow files",
            )
            install_flow_group.add_argument("--name", type=str, help="Flow name mask of the flow(s)")
            install_flow_group.add_argument("--tag", type=str, help="Flow tags mask of the flow(s)")

        subparser.add_argument("--backend_dir", type=str, help="Directory for the backend")
        if i[0] == "run":
            subparser.add_argument("--host", type=str, help="Host to listen (DEFAULT or SERVER mode)")
            subparser.add_argument("--port", type=str, help="Port to listen (DEFAULT or SERVER mode)")
            subparser.add_argument("--server", type=str, help="Address of Vix Server (WORKER mode)")
            subparser.add_argument("--tasks_files_dir", type=str, help="Directory for input/output files")
            subparser.add_argument("--mode", choices=["WORKER", "SERVER"], help="VIX special operating mode")
            subparser.add_argument("--ui", nargs="?", default="", help="Enable WebUI (DEFAULT or SERVER mode)")
            subparser.add_argument("--disable-device-detection", action="store_true", default=False)
            comfyui.add_arguments(subparser)

    args = parser.parse_args()

    defined_loglvl = get_log_level(args.verbose)
    logging.basicConfig(
        level=defined_loglvl,
        format="%(asctime)s: [%(funcName)s]:%(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(get_higher_log_level(defined_loglvl))

    if args.command == "run":
        if args.host:
            options.VIX_HOST = args.host
        if args.port:
            options.VIX_PORT = args.port
        if args.ui is None:  # `--ui` without value: enable default UI
            options.UI_DIR = str(importlib.resources.files("visionatrix").joinpath("client"))
        elif args.ui != "":
            options.UI_DIR = args.ui
        if args.mode:
            options.VIX_MODE = args.mode
        if args.server:
            options.VIX_SERVER = args.server

    database.init_database_engine()

    if args.command == "create-user":
        database.create_user(args.name, args.full_name, args.email, args.password, args.admin, args.disabled)
        sys.exit(0)

    options.init_dirs_values(
        backend=getattr(args, "backend_dir", ""),
        tasks_files=getattr(args, "tasks_files_dir", ""),
    )

    if args.command == "install":
        comfyui_dir = Path(options.BACKEND_DIR)
        if comfyui_dir.exists():
            c = input("Do you want to reinstall the ComfyUI folder? (Y/N): ").lower()
            if c != "y":
                print("Skipping ComfyUI re-installation.")
                sys.exit(0)
            comfyui_models = comfyui_dir.joinpath("models")
            comfyui_models_size = sum(file.stat().st_size for file in comfyui_models.rglob("*") if file.is_file())
            comfyui_models_size_gb = round(comfyui_models_size / (1024**3), 1)
            logging.getLogger("visionatrix").debug("Size of ComfyUI models dir: %s GB", comfyui_models_size_gb)
            if comfyui_models_size_gb > 3.9:  # Threshold in GB
                c = input(
                    f"The ComfyUI folder is approximately {comfyui_models_size_gb} GB. "
                    "Are you sure you want to proceed and clear this folder? (Y/N): "
                ).lower()
                if c != "y":
                    print("Skipping backend re-installation.")
                    sys.exit(0)
        install()
    elif args.command == "update":
        update()
    elif args.command == "run":
        run_vix()
    elif args.command == "install-flow":
        comfyui.load(None)
        r = True
        if args.file:
            path = Path(args.file)
            if path.is_file():
                with path.open("rb") as fp:
                    install_flow_comfy = json.loads(fp.read())
                r = install_custom_flow(get_vix_flow(install_flow_comfy), install_flow_comfy)
            elif path.is_dir():
                json_files = list(path.glob("*.json"))
                if not json_files:
                    logging.getLogger("visionatrix").error("No JSON files found in directory: '%s'", path)
                    sys.exit(2)
                if len(json_files) > 1:
                    logging.getLogger("visionatrix").info("Multiple JSON files found in directory: '%s'", path)

                for json_file in json_files:
                    logging.getLogger("visionatrix").info("Installing flow from file: '%s'", json_file)
                    with json_file.open("rb") as fp:
                        install_flow_comfy = json.loads(fp.read())
                    if not install_custom_flow(get_vix_flow(install_flow_comfy), install_flow_comfy):
                        r = False
            else:
                logging.getLogger("visionatrix").error("Path is neither a file nor a directory: '%s'", path)
                sys.exit(2)
        else:
            flows_comfy = {}
            not_installed_flows = get_not_installed_flows(flows_comfy)
            if args.tag:
                flow_install_pattern = str(args.tag)
                flows_to_install = {}
                for flow_name, flow in not_installed_flows.items():
                    if any(fnmatchcase(tag, flow_install_pattern) for tag in flow.tags):
                        flows_to_install[flow_name] = flow
            else:
                flow_install_pattern = str(args.name).lower()
                flows_to_install = {
                    name: flow for name, flow in not_installed_flows.items() if fnmatchcase(name, flow_install_pattern)
                }
            if not flows_to_install:
                logging.getLogger("visionatrix").error("No flows found matching pattern: '%s'", flow_install_pattern)
                sys.exit(2)
            if len(flows_to_install) > 1:
                logging.getLogger("visionatrix").warning("Multiple flows match pattern: '%s'", flow_install_pattern)
                for flow_name, flow in flows_to_install.items():
                    logging.getLogger("visionatrix").warning(" - %s (tags: %s)", flow_name, ", ".join(flow.tags))
                confirm = input("Do you want to install all of them? (Y/N): ").lower()
                if confirm != "y":
                    logging.getLogger("visionatrix").info("Aborting installation.")
                    sys.exit(0)
            for flow_name, flow in flows_to_install.items():
                if not install_custom_flow(flow=flow, flow_comfy=flows_comfy[flow_name]):
                    r = False
        if not r:
            sys.exit(1)
    elif args.command == "orphan-models":
        comfyui.load(None)
        process_orphan_models(args.dry_run, args.no_confirm, args.include_useful_models)
    elif args.command == "openapi":
        comfyui.load(None)
        flows_arg = args.flows.strip()
        skip_not_installed = args.skip_not_installed
        openapi_schema = generate_openapi(flows_arg, skip_not_installed, args.exclude_base)
        with builtins.open(args.file, "w", encoding="UTF-8") as f:
            openapi_schema_str = json.dumps(openapi_schema, indent=args.indentation)
            if not openapi_schema_str.endswith("\n"):
                openapi_schema_str += "\n"
            f.write(openapi_schema_str)
    else:
        logging.getLogger("visionatrix").error("Unknown command: '%s'", args.command)
        sys.exit(2)
    sys.exit(0)
