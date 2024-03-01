import argparse
import sys

from . import install, update
from . import options

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    install_parser = subparsers.add_parser("install", help="Performs cleanup & initialization")
    install_parser.add_argument("--backend_dir", type=str, help="Directory for the backend")
    install_parser.add_argument("--flows_dir", type=str, help="Directory for the flows")
    install_parser.add_argument("--models_dir", type=str, help="Directory for the models")

    update_parser = subparsers.add_parser("update", help="Performs update to the latest version")
    update_parser.add_argument("--backend_dir", type=str, help="Directory for the backend")
    update_parser.add_argument("--flows_dir", type=str, help="Directory for the flows")
    update_parser.add_argument("--models_dir", type=str, help="Directory for the models")

    args = parser.parse_args()
    if args.command == "install":
        sys.exit(install(backend_dir=args.backend_dir, flows_dir=args.flows_dir, models_dir=args.models_dir))
    elif args.command == "update":
        sys.exit(update(backend_dir=args.backend_dir, flows_dir=args.flows_dir, models_dir=args.models_dir))
    else:
        print("Unknown command")
    sys.exit(2)
