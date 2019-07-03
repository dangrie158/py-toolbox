"""
Automatic task progress and monitoring notification via E-Mail.
Especially useful to supervise long-running tasks
"""

import smtplib
import logging
import inspect
import linecache
import threading
from typing import (
    Union,
    Any,
    Optional,
    Generator,
    ContextManager,
    Sequence,
    IO,
    TypeVar,
    cast,
)
from types import FrameType
from datetime import timedelta
from socket import getfqdn
from contextlib import contextmanager, nullcontext
from email.message import EmailMessage
from io import StringIO  # pylint: disable=no-name-in-module
from textwrap import dedent

from pytb.config import current_config
from pytb.io import mirrored_stdstreams, render_text

# Union type for a general time interval in (fractional) seconds
_Interval = Union[int, float, timedelta]

# Generic Type Variable to indicate Type of Iterable
_IterType = TypeVar("_IterType")


def _get_caller_code_fragment(caller_frame: FrameType, context_size: int = 3) -> str:
    """
    Create a string representation of the code that called the Notify.
    The code block returned is selected using the following rules:

    1. If the calling line is unindented, add a conext of
        the surrounding ``context_size`` lines
    2. If the calling line is in any indentation level > 0,
        return all lines above and below that are also indented

    An indentet line is any line with a leading whitespace.

    Each line in the code block is prefixed with its linenumber within the file and
    the calling ine is marked with an arrow ('--->')

    :param caller_frame: The stack frame to use for code representation
    :param context_size: Number of lines of context to add above and below
        if the calling code is unindented

    Example:

    .. testsetup:: *

        from pytb.notification import Notify

    .. doctest::

        >>> import inspect
        >>> def test():
        ...     x = 1 + 1
        ...     frame = inspect.currentframe()
        ...     y = 2 + 2
        ...     return frame
        >>> frame = test()
        >>> code_block = _get_caller_code_fragment(frame)
        >>> print(code_block)
             2: def test():
             3:     x = 1 + 1
             4:     frame = inspect.currentframe()
        ---> 5:     y = 2 + 2
             6:     return frame

    """
    filename = caller_frame.f_code.co_filename
    lineno = caller_frame.f_lineno
    caller_file_lines = linecache.getlines(filename)

    def get_indentation(line: str) -> int:
        level = 0
        for char in line:
            if char in ("\t", " "):
                level += 1
            else:
                return level
        return level

    levels = [get_indentation(line) for line in caller_file_lines]

    # -1 from lineno because line numbers are 1-indexed
    block_start = block_end = lineno - 1

    # move the start and end line to the block boundaries
    # (next occurence of unindented line)
    while block_start > 0 and levels[block_start] > 0:
        # move up a line
        block_start -= 1

    while len(levels) < block_end and levels[block_end] > 0:
        # move down a line
        block_end += 1

    if block_start == block_end:
        # add some context, otherwise the caller
        # would only be a single line
        block_start = max(0, block_start - context_size)
        block_end = min(block_end + context_size, len(caller_file_lines))

    code_block_lines = caller_file_lines[block_start : block_end + 1]
    code_block = ""

    # count the number of characters that are needed to represent
    # the biggest possible line number
    space_for_linenos = len(str(len(caller_file_lines)))
    for block_lineno, line in enumerate(code_block_lines):
        cur_lineno = block_start + block_lineno + 2
        prefix = "--->" if cur_lineno == lineno else "    "
        code_block += f"{prefix} {str(cur_lineno).ljust(space_for_linenos)}: {line}"

    # remove any training whitespaces and newlines
    return code_block.rstrip()


def _get_caller_frame(level: int) -> Optional[FrameType]:
    """
    Get the frame of the calling code of this function

    :param level: The number of frames to pop from the stack before
        returning the caller
    """
    caller_frame = inspect.currentframe()
    # this function itself adds a frame stack entry we need to go up
    level += 1
    while level > 0:
        level -= 1
        caller_frame = getattr(caller_frame, "f_back")
    return caller_frame


class Notify:
    """
    A :class:`Notify` object captures the basic configuration of how a
    notification should be handled.

    The methods :meth:`when_done`, :meth:`every` and :meth:`when_stalled`
    are reenterable context managers. Thus a single :class:`Notify` object
    can be reused at several places and different context-managers can be
    reused in the same context.

    Overwrite the method :meth:`_send_notification` in a derived class to
    specify a custom handling of the notifications

    :param task: A short description of the monitored block.
    :param render_outputs: If true, prerender the oputputs using :meth:`pytb.io.render_text`
        This may be useful if the captured codeblock produces progressbars using carriage returns
    """

    def __init__(self, task: str, render_outputs: bool = True):
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        self.task = task
        self.render_outputs = render_outputs

    def now(self, message: str) -> None:
        """
        Send a manual notification now. This will use the provided ``message`` as
        the ``reason`` placeholder. No output can be capured using this function.

        :param message: A string used to fill the ``{reason}`` placeholder of the notification
        """
        caller_frame = _get_caller_frame(1)
        self._send_notification(
            self.task, message, caller_frame, "<output not available>"
        )

    @contextmanager
    def when_done(
        self,
        only_if_error: bool = False,
        capture_output: bool = True,
        caller_frame: Optional[FrameType] = None,
        reason_prefix: str = "",
    ) -> Generator[None, None, None]:
        """
        Create a context that, when exited, will send notifications.
        If an unhandled exception is raised during execution, a notification
        on the failure of the execution is sent. If the context exits cleanly,
        a notification is only sent if ``only_if_error`` is set to ``False``

        By default, all output to the ``stdio`` and ``stderr`` streams is
        captured and sent in the notification. If you expect huge amounts of
        output during the execution of the monitored code, you can disable
        the capturing with the ``capture_output`` parameter.

        To not spam you with notification when you stop the code execution
        yourself, ``KeyboardInterrupt`` exceptions will not trigger a notification.

        :param only_if_error: if the context manager exits cleanly, do not send
            any notifications
        :param capture_output: capture all output to the ``stdout`` and ``stderr``
            stream and append it to the notification
        :param caller_frame: the stackframe to use when determining the code block
            for the notification. If None, the stackframe of the line that called
            this function is used
        :param reason_prefix: an additional string that is prepended to the ``reason``
            placeholder when sending a notification. Used to implement :meth:`on_iteration_of`.
        """

        # if called from user code, the calling frame is unspecified. save it fur future reference
        if caller_frame is None:
            # we need to go 2 frames up because the direct parent is the
            # contextmanagers ``__enter__`` method`
            caller_frame = _get_caller_frame(2)

            # only print the debug message when this context is not invoked
            # from another context in this notifier
            self._logger.info(f"Entering when-done Context")

        output_buffer = StringIO()
        output_handler = cast(
            ContextManager[None],
            mirrored_stdstreams(output_buffer) if capture_output else nullcontext(),
        )

        exception = None

        # pylint: disable=broad-except
        try:
            with output_handler:
                yield
        except Exception as current_exception:
            exception = current_exception

        output = (
            output_buffer.getvalue()
            if capture_output
            else "<output capturing disabled>"
        )

        if exception is None and only_if_error:
            self._logger.info(
                f"Notification context left without error. Not firing notification"
            )
            return

        if exception is not None:
            self._send_notification(
                self.task,
                f"{reason_prefix} failed".lstrip(),
                caller_frame,
                output,
                exception,
            )
            raise exception

        self._send_notification(
            self.task, f"{reason_prefix} done".lstrip(), caller_frame, output
        )

    @contextmanager
    def every(
        self,
        interval: _Interval,
        incremental_output: bool = False,
        caller_frame: Optional[FrameType] = None,
    ) -> Generator[None, None, None]:
        """
        Send out notifications with a fixed interval to receive progress updates.
        This contextmanager wraps a :meth:`when_done`, so it is guaranteed to send
        to notify at least once upon task completion or error.

        :param interval: ``float``, ``int`` or ``datetime.timedelta`` object representing the
            number of seconds between notifications
        :param incremental_output: Only send incremental output summaries with each update.
            If ``False`` the complete captured output is sent each time
        :param caller_frame: the stackframe to use when determining the code block for
            the notification. If None, the stackframe of the line that called this
            function is used
        """

        # if called from user code, the calling frame is unspecified. save it fur future reference
        if caller_frame is None:
            # we need to go 2 frames up because the direct parent
            # is the contextmanagers ``__enter__`` method`
            caller_frame = _get_caller_frame(2)

        output_buffer = StringIO()
        output_handler = mirrored_stdstreams(output_buffer)

        def send_progress() -> None:
            self._logger.info("sending out scheduled notifications")
            output = output_buffer.getvalue()
            # clear the output buffer between progress notification
            # if we only should send incremental updates of the output
            if incremental_output:
                output_buffer.truncate(0)

            self._send_notification(self.task, "progress update", caller_frame, output)

        progress_sender = Timer(send_progress)
        progress_sender.call_every(interval)

        try:
            with self.when_done(False, True, caller_frame=caller_frame):
                with output_handler:
                    yield
        finally:
            # stop the scheduled sending of progress updates
            progress_sender.stop()

    @contextmanager
    def when_stalled(
        self,
        timeout: _Interval,
        capture_output: bool = True,
        caller_frame: Optional[FrameType] = None,
    ) -> Generator[None, None, None]:
        """
        Monitor the output of the code bock to determine a possible stall of the execution.
        The execution is considered to be stalled when no new output is produced within
        ``timeout`` seconds.

        Only a single notification is sent each time a stall is detected.
        If a stall notification was sent previously, new output will cause a notification to
        be sent that the stall was resolved.

        Contrary to the :meth:`every` method, this does not wrap the context into a
        :meth:`when_done` function, thus it may never send a notification. If you want,
        you can simply use the same :class:`Notify` to create mutliple contexts:

        .. code-block:: python

            with notify.when_stalled(timeout), notify.when_done():
                # execute some potentially long-running process

        However, it will always send a notification if the code block  exits with an exception.

        :param timeout: maximum number of seconds where no new output is produced
            before the code block is considiered to be stalled
        :param capture_output: append all output to ``stdout`` and ``stderr`` to the notification
        :param caller_frame: the stackframe to use when determining the code block for
            the notification. If None, the stackframe of the line that called this
            function is used
        """

        # if called from user code, the calling frame is unspecified. save it fur future reference
        if caller_frame is None:
            # we need to go 2 frames up because the direct parent is
            # the contextmanagers ``__enter__`` method`
            caller_frame = _get_caller_frame(2)

        output_buffer = StringIO()
        output_handler = mirrored_stdstreams(output_buffer)

        last_output = output_buffer.getvalue()
        was_stalled = False

        def check_stalled() -> None:
            nonlocal last_output, was_stalled

            self._logger.info("Checking for stalled code block")

            output = output_buffer.getvalue()
            output_in_notification = (
                output_buffer.getvalue()
                if capture_output
                else "<output capturing disabled>"
            )
            if output == last_output and not was_stalled:
                # we're probably stalled. send out a notification
                self._send_notification(
                    self.task, "probably stalled", caller_frame, output_in_notification
                )
                was_stalled = True
            elif was_stalled:
                # wrong alert previously, send a notification that everything is ok again
                self._send_notification(
                    self.task, "no longer stalled", caller_frame, output_in_notification
                )
                was_stalled = False

            last_output = output

        stall_checker = Timer(check_stalled)
        stall_checker.call_every(timeout)

        try:
            with self.when_done(True, capture_output, caller_frame=caller_frame):
                with output_handler:
                    yield
        finally:
            # stop the scheduled sending of progress updates
            stall_checker.stop()

    def on_iteration_of(
        self,
        iterable: Sequence[_IterType],
        capture_output: bool = True,
        after_every: int = 1,
        caller_frame: Optional[FrameType] = None,
    ) -> Generator[_IterType, None, None]:
        """
        Send a message *after* each iteration of an iterable. The current iteration
        and total number of iterations (if the iterable implements :meth:`len`)
        will be part of the ``reason`` placeholder in the notification.

        .. code-block:: python

            for x in notify.on_iteration_of(range(5)):
                # execute some potentially long-running process on x

        :param iterable: the iterable which items will be yielded by this generator
        :param capture_output: capture all output to the ``stdout`` and ``stderr``
            stream and append it to the notification
        :param after_every: Only notify about each N-th iteration
        :param caller_frame: the stackframe to use when determining the code block
            for the notification. If None, the stackframe of the line that called
            this function is used
        """

        if caller_frame is None:
            caller_frame = _get_caller_frame(1)

        total_iterations = str(len(iterable)) if hasattr(iterable, "__len__") else "???"

        for iteration, item in enumerate(iterable):
            iteration_num = iteration + 1
            notification_context = nullcontext()
            if (
                iteration_num % after_every == 0
                or str(iteration_num) == total_iterations
            ):
                notification_context = self.when_done(
                    capture_output=capture_output,
                    only_if_error=False,
                    caller_frame=caller_frame,
                    reason_prefix=f"Iteration {iteration_num}/{total_iterations}",
                )

            with notification_context:
                yield item

    def _send_notification(
        self,
        task: str,
        reason: str,
        caller_frame: Optional[FrameType],
        output: str,
        exception: Optional[Exception] = None,
    ) -> None:
        """
        Handle the actual notification. Overwrite this method to specify your own Notifier
        over any communication mechanism you may desire.
        """
        raise NotImplementedError()


class NotifyViaEmail(Notify):
    """
    A :class:`NotifyViaEmail` object uses an SMTP connection to send notification via emails.
    The SMTP server is configured either at runtime or via the effective ``.pytb.config``
    files ``notify`` section.

    :param email_addresses: a single email address or a list of addresses. Each entry is a seperate
        recipient of the notification send by this ``Notify``
    :param task: A short description of the monitored block.
    :param sender: Sender name to use. If empty, use this machines FQDN
    :param smtp_host: The SMTP servers address used to send the notifications
    :param smtp_port: The TCP port of the SMTP server
    :param smtp_ssl: Whether or not to use SSL for the SMTP connection

    All optional parameters are initialized from the effective ``.pytb.config``
    if they are passed ``None``
    """

    message_template = dedent(
        """\
        Hello {recipient},
        {task} {reason}. {exinfo}

        {code_block}

        produced output:

        {output}
    """
    )
    """
    The message template used to create the message content.

    You can customize it by overwriting the instance-variable or by
    deriving your custom :class:`NotifyViaEmail`.

    The following placeholders are available:

    - ``task``
    - ``sender``
    - ``recipient``
    - ``reason``
    - ``exinfo``
    - ``code_block``
    - ``output``
    """

    subject_template = "{task} on {sender} {reason}"
    """
    The template that is used as subject line in the mail.

    You can customize it by the same techniques as the :attr:`message_template`.
    The same placeholders are available.
    """

    def __init__(
        self,
        task: str,
        email_addresses: Optional[Sequence[str]] = None,
        sender: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_ssl: Optional[bool] = None,
    ):
        super().__init__(task)

        notify_config = current_config["notify"]

        if isinstance(email_addresses, str):
            email_addresses = list(email_addresses)
        if email_addresses is None:
            email_addresses = notify_config.getlist("email_addresses")

        if smtp_host is None:
            smtp_host = notify_config.get("smtp_host")

        if smtp_port is None:
            smtp_port = notify_config.getint("smtp_port")

        if smtp_ssl is None:
            smtp_ssl = notify_config.getboolean("smtp_ssl")

        if sender is None:
            sender = notify_config.get("sender")
        if not sender:
            sender = f"notify@{getfqdn()}"
        self.sender = sender

        if not email_addresses:
            self._logger.warning(
                "email_addresses is an empty list, no emails will be sent"
            )
            self.smtp_class = None
        else:
            self._logger.info(
                f"Notify object configured to send emails to {email_addresses}"
            )
            self.email_addresses = email_addresses
            self.smtp_class = smtplib.SMTP_SSL if smtp_ssl else smtplib.SMTP
            self.smtp_host = smtp_host
            self.smtp_port = smtp_port

    def _create_message(
        self,
        recipient: str,
        task: str,
        reason: str,
        caller_frame: Optional[FrameType],
        output: str,
        exception: Optional[Exception] = None,
    ) -> EmailMessage:
        if caller_frame is not None:
            code_block = _get_caller_code_fragment(caller_frame)
        else:
            code_block = "<caller not available>"

        output = "<No output produced>" if not output else output
        exinfo = (
            f"\n\nThe following exception occurred:\n{str(exception)}\n"
            if exception is not None
            else ""
        )

        subject = self.subject_template.format(
            task=task,
            sender=self.sender,
            recipient=recipient,
            reason=reason,
            exinfo=exinfo,
            code_block=code_block,
            output=output,
        )

        content = self.message_template.format(
            task=task,
            sender=self.sender,
            recipient=recipient,
            reason=reason,
            exinfo=exinfo,
            code_block=code_block,
            output=output,
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = recipient
        msg.set_content(content)
        msg.set_type("text/plain")
        return msg

    def _send_notification(
        self,
        task: str,
        reason: str,
        caller_frame: Optional[FrameType],
        output: str,
        exception: Optional[Exception] = None,
    ) -> None:

        if self.render_outputs:
            output = render_text(output)

        messages = (
            self._create_message(address, task, reason, caller_frame, output, exception)
            for address in self.email_addresses
        )

        if self.smtp_class is not None:
            # pylint: disable=broad-except
            try:
                with self.smtp_class(self.smtp_host, self.smtp_port) as smtp:
                    for message in messages:
                        self._logger.info(f"sending message to {message['To']}")
                        smtp.send_message(message)
            except Exception as current_exception:
                # we do not want to disrupt the user program if we fail to send the message
                self._logger.exception(
                    f"error during sending of notification", current_exception
                )


class NotifyViaStream(Notify):
    """
    :class:`NotifyViaStream` will write string representations of notifications
    to the specified writable ``stream``. This may be useful when the stream is
    a UNIX or TCP socket.

    Also useful when when the stream is a ``io.StringIO`` object for testing.

    The string representation of the notification can be configured via the
    :attr:`notification_template` attribute which can be overwritten on a
    per-instance basis.

    :param task: A short description of the monitored block.
    :param stream: A writable stream where notification should be written to.
    """

    notification_template = "{task}\t{reason}\t{exinfo}\t{output}\n"
    """
    The string that is written to the stream after replacing all placeholders
    with the notifications properties.

    The following placeholders are available

    - ``task``
    - ``reason``
    - ``exinfo``
    - ``code_block``
    - ``output``
    """

    def __init__(self, task: str, stream: IO[Any]):
        super().__init__(task)
        self.stream = stream

    def _send_notification(
        self,
        task: str,
        reason: str,
        caller_frame: Optional[FrameType],
        output: str,
        exception: Optional[Exception] = None,
    ) -> None:
        if caller_frame is not None:
            code_block = _get_caller_code_fragment(caller_frame)
        else:
            code_block = "<caller not available>"

        output = "<No output produced>" if not output else output.strip()

        if self.render_outputs:
            output = render_text(output)

        exinfo = f"{str(exception)}" if exception is not None else ""

        content = self.notification_template.format(
            task=task,
            reason=reason,
            exinfo=exinfo,
            code_block=code_block,
            output=output,
        )

        self.stream.write(content)


class Timer(threading.Thread):
    r"""
    A gracefully stoppable Thread with means to run a target function
    repedatley every ``X`` seconds.

    :param target: the target function that will be executed in the thread
    :param \*args: additional positional parameters passed to the target function
    :param \**kwargs: additional keyword parameters passed to the target function
    """

    def __init__(
        self,
        # something goes wrong when declaring the real type of the callable
        # and running the tests with unittest. so, for now lets use a simple
        # any type until this is fixed
        target: Any,  #: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.interval: float = -1
        self._stop_event = threading.Event()
        super().__init__()

    def stop(self) -> None:
        """
        schedule the thread to stop. This is only meant to be used to stop
        a repeated scheduling of the target funtion started via :meth:`call_every`
        but will not interrupt a long-running target function

        :raises RuntimeError: if the thread was not started via :meth:`call_every`
        """
        if self._stop_event is None:
            raise RuntimeError("thread not started via 'run_every' function")

        self._stop_event.set()

    def call_every(self, interval: _Interval) -> None:
        """
        start the repeated execution of the target function every ``interval`` seconds.
        The target function is first invoked after waiting the interval. If the thread
        is stopped before the first interval passed, the target function may never be called

        :param interval: ``float``, ``int`` or ``datetime.timedelta`` object representing the
            number of seconds between invocations of the target function
        """
        # make sure the interval is number representing fractional seconds
        if isinstance(interval, timedelta):
            interval = interval.total_seconds()

        self.interval = float(interval)

        self.start()

    def run(self) -> None:
        if self.interval == -1:
            # this thread was not started via the ``call_every()``
            # method, exit after the first execution
            self.target(*self.args, **self.kwargs)
        else:
            while True:
                self._stop_event.wait(self.interval)
                # check if we got stopped while sleeping
                # in this case, do not run the target again
                if self._stop_event.is_set():
                    break
                self.target(*self.args, **self.kwargs)

            self._stop_event.clear()
            self.interval = -1
