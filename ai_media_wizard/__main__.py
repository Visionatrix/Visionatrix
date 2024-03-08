import argparse
import builtins
import json
import logging
import sys

from . import install, options, run_backend, update
from .flows import install_custom_flow


def get_log_level(log_level_str):
    """Convert log level string to logging module log level."""
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return log_levels.get(log_level_str.upper(), logging.INFO)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--loglevel",
        type=str,
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        default="INFO",
    )
    subparsers = parser.add_subparsers(dest="command")
    for i in [
        ("install", "Performs cleanup & initialization"),
        ("update", "Performs update to the latest version"),
        ("run", "Starts the AI and MediaWizard backends"),
        ("install-flow", "Install flow from folder"),
    ]:
        subparser = subparsers.add_parser(i[0], help=i[1])
        if i[0] == "install-flow":
            subparser.add_argument("--flow", type=str, help="Path to `flow.json`", required=True)
            subparser.add_argument("--flow_comfy", type=str, help="Path to `xyz_comfy.json`", required=True)
        else:
            subparser.add_argument("--backend_dir", type=str, help="Directory for the backend")
        subparser.add_argument("--flows_dir", type=str, help="Directory for the flows")
        subparser.add_argument("--models_dir", type=str, help="Directory for the models")
        if i[0] == "run":
            subparser.add_argument("--host", type=str, help="Host to be used by Wizard backend")
            subparser.add_argument("--port", type=str, help="Port to be used by Wizard backend")
            subparser.add_argument("--ui", type=str, help="Folder with UI")

    args = parser.parse_args()
    logging.basicConfig(
        level=get_log_level(args.loglevel),
        format="%(asctime)s: [%(funcName)s]:%(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.command == "install":
        sys.exit(install(backend_dir=args.backend_dir, flows_dir=args.flows_dir, models_dir=args.models_dir))
    elif args.command == "update":
        sys.exit(update(backend_dir=args.backend_dir, flows_dir=args.flows_dir, models_dir=args.models_dir))
    elif args.command == "run":
        sys.exit(
            run_backend(
                backend_dir=args.backend_dir,
                flows_dir=args.flows_dir,
                models_dir=args.models_dir,
                wizard_host=args.host,
                wizard_port=args.port,
                ui_dir=args.ui,
            )
        )
    elif args.command == "install-flow":
        with builtins.open(args.flow, "rb") as fp:
            flow = json.loads(fp.read())
        with builtins.open(args.flow_comfy, "rb") as fp:
            flow_comfy = json.loads(fp.read())
        install_custom_flow(
            flows_dir=options.get_flows_dir(args.flows_dir),
            models_dir=options.get_models_dir(args.models_dir),
            flow=flow,
            flow_comfy=flow_comfy,
        )
        sys.exit(0)
    else:
        logging.getLogger("ai_media_wizard").error("Unknown command")
    sys.exit(2)
