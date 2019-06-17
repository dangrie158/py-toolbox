import argparse
import sys
import traceback
import logging
from contextlib import ExitStack
from pathlib import Path
from pdb import Restart as PdbRestart
from pathlib import Path
import runpy

from .config import current_config
from .rdb import RdbClient, Rdb
from .notification import NotifyViaStream, NotifyViaEmail


def to_stream(stream_name):
    if stream_name == "<stdout>":
        return sys.__stdout__
    elif stream_name == "<stderr>":
        return sys.__stderr__
    else:
        stream_file = Path(stream_name)
        if not stream_file.exists() or not stream_file.is_file():
            raise argparse.ArgumentTypeError(f"{stream_name} is not a file")
        else:
            try:
                return stream_file.open("a")
            except:
                raise argparse.ArgumentTypeError(
                    f"could not open {stream_name} for writing"
                )


def main():
    _logger = logging.getLogger()

    parser = argparse.ArgumentParser(
        prog="pytb", description="Python Toolkit CLI Interface"
    )
    subcommands = parser.add_subparsers(help="sub-command", dest="command")

    notify_parser = subcommands.add_parser(
        "notify", help="Statusnotification about long-running tasks."
    )

    notify_parser.add_argument(
        "--every", help="Send a notification every X seconds", metavar="X", type=int
    )
    notify_parser.add_argument(
        "--when-stalled",
        help="Send a notification if the script seems to be stalled for more than X seconds",
        metavar="X",
        type=int,
    )
    notify_parser.add_argument(
        "--when-done",
        action="store_true",
        default=False,
        help="Send a notification whenever the script finishes",
    )
    notify_subcommands = notify_parser.add_subparsers(help="notifier", dest="notifier")
    notify_config = current_config["notify"]

    notify_via_email = notify_subcommands.add_parser("via-email")
    notify_via_email.add_argument(
        "--recipients",
        nargs="+",
        help="Recipient addresses for the notifications",
        default=notify_config["email_addresses"],
    )
    notify_via_email.add_argument(
        "--smtp-host",
        help="Address of the external SMTP Server used to send notifications via E-Mail",
        default=notify_config["smtp_host"],
    )
    notify_via_email.add_argument(
        "--smtp-port",
        type=int,
        help="Port the external SMTP Server listens for incoming connections",
        default=notify_config["smtp_port"],
    )
    notify_via_email.add_argument(
        "--sender",
        help="Sender Address for notifications",
        default=notify_config["sender"],
    )
    notify_via_email.add_argument(
        "--use-ssl",
        action="store_true",
        help="Use a SSL connection to communicate with the SMTP server",
        default=notify_config["smtp_ssl"],
    )
    notify_via_email.add_argument(
        "-m",
        action="store_true",
        help="Load an executable module or package instead of a file",
        default=False,
        dest="run_as_module",
    )
    notify_via_email.add_argument("script", help="script path or module name to run")
    notify_via_email.add_argument(
        "args",
        help="additional parameter passed to the script",
        nargs=argparse.REMAINDER,
        metavar="args",
    )

    notify_via_stream = notify_subcommands.add_parser("via-stream")
    notify_via_stream.add_argument(
        "--stream",
        help="The writable stream. This can be a filepath or the special values `<stdout>` or `<stderr>`",
        type=to_stream,
        required=True,
    )
    notify_via_stream.add_argument(
        "-m",
        action="store_true",
        help="Load an executable module or package instead of a file",
        default=False,
        dest="run_as_module",
    )
    notify_via_stream.add_argument("script", help="script path or module name to run")
    notify_via_stream.add_argument(
        "args",
        help="additional parameter passed to the script",
        nargs=argparse.REMAINDER,
        metavar="args",
    )

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

    if not args.command:
        parser.error("You need to specify a subcommand")

    elif args.command == "rdb":
        if not args.function:
            rdb_parser.error("You need to specify the function")

        elif args.function == "client":
            # create the client instance
            _logger.info(
                f"trying to connect to remote debugger at {args.host}:{args.port}..."
            )
            try:
                RdbClient(args.host, args.port)
                _logger.warn(f"connection to {args.host}:{args.port} closed.")
            except ConnectionRefusedError:
                _logger.error(f"connection to {args.host}:{args.port} refused.")
                sys.exit(2)

        elif args.function == "server":
            mainpyfile = Path(args.script)
            if not args.run_as_module and not mainpyfile.exists():
                _logger.error(f"{args.script} does not exist")
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
                    _logger.info("The program finished and will be restarted")
                except PdbRestart:
                    _logger.info(
                        f"Restarting {mainpyfile} with arguments:\n\t {' '.join(args.args)}"
                    )
                except SystemExit:
                    # In most cases SystemExit does not warrant a post-mortem session.
                    _logger.info(
                        "The program exited via sys.exit(). Exit status:", end=" "
                    )
                    _logger.info(sys.exc_info()[1])
                except SyntaxError:
                    traceback.print_exc()
                    rdb.do_quit(None)
                    sys.exit(1)
                except:
                    traceback.print_exc()
                    _logger.error("Uncaught exception. Entering post mortem debugging")
                    _logger.error("Running 'cont' or 'step' will restart the program")
                    t = sys.exc_info()[2]
                    rdb.interaction(None, t)
                    _logger.info(
                        f"Post mortem debugger finished. The {mainpyfile} will be restarted"
                    )

            rdb.do_quit(None)

    elif args.command == "notify":
        if not args.when_done and args.every is None and args.when_stalled is None:
            notify_parser.error(
                "You need to specify at least one of the notification options --when-done, --every or --when-stalled\n"
            )

        if not args.notifier:
            notify_parser.error(
                "You need to specify the notification system to use (EMail or Stream"
            )

        elif args.notifier == "via-stream":
            notifier = NotifyViaStream(task=args.script, stream=args.stream)

        elif args.notifier == "via-email":
            if len(args.recipients) == 0:
                notify_via_email.error(
                    "Make sure to include at least one recipient via the .pytb.conf or via the --recipients option\n"
                )

            notifier = NotifyViaEmail(
                task=args.script,
                email_addresses=args.recipients,
                sender=args.sender,
                smtp_host=args.smtp_host,
                smtp_port=args.smtp_port,
                smtp_ssl=args.use_ssl,
            )

        notifier_context = []
        if args.when_stalled is not None:
            notifier_context.append(notifier.when_stalled(args.when_stalled))
        if args.every is not None:
            notifier_context.append(notifier.every(args.every))
        if args.when_done:
            notifier_context.append(notifier.when_done())

        # assemble the execution environemnt for the script to run
        script_globals = {"__name__": "__main__"}
        if args.run_as_module:
            mod_name, mod_spec, code = runpy._get_module_details(args.script)
            script_globals.update(
                {
                    "__file__": code.co_filename,
                    "__package__": mod_spec.parent,
                    "__loader__": mod_spec.loader,
                    "__spec__": mod_spec,
                }
            )
        else:
            mainpyfile = Path(args.script)
            # Replace this modules dir with script's dir in front of module search path.
            sys.path[0] = str(mainpyfile.parent)
            with mainpyfile.open("rb") as fp:
                code = compile(fp.read(), args.script, "exec")

            script_globals.update({"__file__": args.script})

        # overwrite the arguments with the user provided args
        sys.argv = [str(args.script)] + args.args

        with ExitStack() as notifiers:
            [notifiers.enter_context(context) for context in notifier_context]

            exec(code, script_globals, script_globals)

        # print(notifier_context)
        # print(args)
        # print(notifier)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    main()
