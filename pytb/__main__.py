import argparse
import sys

from .config import current_config
from .rdb import RdbClient, Rdb

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="pytb", description="Python Toolkit CLI Interface"
    )
    subcommands = parser.add_subparsers(help="sub-command", dest="command")

    rdb_parser = subcommands.add_parser("rdb", help="Remote debugging over TCP")
    rdb_subcommands = rdb_parser.add_subparsers(help="function", dest="function")
    rdb_config = current_config["rdb"]

    rdb_server = rdb_subcommands.add_parser("server")
    rdb_server.add_argument(
        "--host",
        help="The interface to bind the socket to",
        default=rdb_config["bind_to"],
    )
    rdb_server.add_argument(
        "--port",
        type=int,
        help="The port to listen for incoming connections",
        default=rdb_config["port"],
    )
    rdb_server.add_argument(
        "--patch-stdio",
        action="store_true",
        help="Redirect stdio streams to the remote client during debugging",
        default=rdb_config["patch_stdio"],
    )

    rdb_client = rdb_subcommands.add_parser("client")
    rdb_client.add_argument(
        "--host",
        help="Remote host where the debug sessino is running",
        default=rdb_config["host"],
    )
    rdb_client.add_argument(
        "--port", type=int, help="Remote port to connect to", default=rdb_config["port"]
    )

    args = parser.parse_args()

    def print_help_and_exit(sub_parser):
        sub_parser.print_help()
        sys.exit(-1)

    if not args.command:
        print_help_and_exit(parser)
    elif args.command == "rdb":
        if not args.function:
            print_help_and_exit(rdb_parser)
        elif args.function == "client":
            # create the client instance
            print(f"trying to connect to remote debugger at {args.host}:{args.port}...")
            try:
                RdbClient(args.host, args.port)
            except ConnectionRefusedError:
                print(f"connection to {args.host}:{args.port} refused")
                sys.exit(-2)
        elif args.function == "server":
            print(args)
