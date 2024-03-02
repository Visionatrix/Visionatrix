import argparse
import sys

from . import install, run_backend, update

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    for i in [
        ("install", "Performs cleanup & initialization"),
        ("update", "Performs update to the latest version"),
        ("run", "Starts the AI and MediaWizard backends"),
    ]:
        subparser = subparsers.add_parser(i[0], help=i[1])
        subparser.add_argument("--backend_dir", type=str, help="Directory for the backend")
        subparser.add_argument("--flows_dir", type=str, help="Directory for the flows")
        subparser.add_argument("--models_dir", type=str, help="Directory for the models")
        if i[0] == "run":
            subparser.add_argument("--host", type=str, help="Host to be used by Wizard backend")
            subparser.add_argument("--port", type=str, help="Port to be used by Wizard backend")

    args = parser.parse_args()
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
            )
        )
    else:
        print("Unknown command")
    sys.exit(2)
