import argparse
import sys
import traceback
from pathlib import Path
from pdb import Restart as PdbRestart

from .config import current_config
from .rdb import RdbClient, Rdb

parser = argparse.ArgumentParser(
    prog="pytb", description="Python Toolkit CLI Interface"
)
subcommands = parser.add_subparsers(help="sub-command", dest="command")

rdb_parser = subcommands.add_parser("rdb", help="Remote debugging over TCP")
rdb_subcommands = rdb_parser.add_subparsers(help="function", dest="function")
rdb_config = current_config["rdb"]

rdb_server = rdb_subcommands.add_parser("server")
rdb_server.add_argument(
    "--host", help="The interface to bind the socket to", default=rdb_config["bind_to"]
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
rdb_server.add_argument(
    "-c",
    help="commands executed before the script is run",
    metavar="commands",
    dest="commands",
)
rdb_server.add_argument(
    "-m",
    action="store_true",
    help="Load an executable module or package instead of a file",
    default=False,
    dest="run_as_module",
)
rdb_server.add_argument("script", help="script path or module name to run")
rdb_server.add_argument(
    "args",
    help="additional parameter passed to the script",
    nargs=argparse.REMAINDER,
    metavar="args",
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
            print(f"connection to {args.host}:{args.port} closed.")
        except ConnectionRefusedError:
            print(f"connection to {args.host}:{args.port} refused.")
            sys.exit(2)

    elif args.function == "server":
        mainpyfile = Path(args.script)
        if not args.run_as_module and not mainpyfile.exists():
            print(f"Error: {args.script} does not exist")
            sys.exit(1)

        # overwrite the arguments with the user provided args
        sys.argv = [str(mainpyfile)] + args.args

        # Replace this modules dir with script's dir in front of module search path.
        if not args.run_as_module:
            sys.path[0] = str(mainpyfile.parent)

        rdb = Rdb(args.host, args.port, args.patch_stdio)
        if args.commands:
            rdb.rcLines.extend(args.commands)

        while True:
            try:
                if args.run_as_module:
                    rdb._runmodule(str(mainpyfile))
                else:
                    rdb._runscript(str(mainpyfile))
                if rdb._user_requested_quit:
                    break
                print("The program finished and will be restarted")
            except PdbRestart:
                print("Restarting", mainpyfile, "with arguments:")
                print("\t" + " ".join(args.args))
            except SystemExit:
                # In most cases SystemExit does not warrant a post-mortem session.
                print("The program exited via sys.exit(). Exit status:", end=" ")
                print(sys.exc_info()[1])
            except SyntaxError:
                traceback.print_exc()
                rdb.do_quit(None)
                sys.exit(1)
            except:
                traceback.print_exc()
                print("Uncaught exception. Entering post mortem debugging")
                print("Running 'cont' or 'step' will restart the program")
                t = sys.exc_info()[2]
                rdb.interaction(None, t)
                print(
                    "Post mortem debugger finished. The "
                    + mainpyfile
                    + " will be restarted"
                )

        rdb.do_quit(None)
