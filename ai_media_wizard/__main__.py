import argparse
import sys

from . import install

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    install_parser = subparsers.add_parser("install", help="Perform cleanup & initialization")
    args = parser.parse_args()
    if args.command == "install":
        sys.exit(install())
    else:
        print("Unknown command")
    sys.exit(2)
