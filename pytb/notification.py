import smtplib
import logging
import inspect
from contextlib import contextmanager, nullcontext
from email.message import EmailMessage
from dataclasses import dataclass
from io import StringIO

from .config import current_config
from .io import mirrored_stdstreams

"""
Automatic task progress and monitoring notification via E-Mail.
Especially useful to supervise long-running tasks
"""


class Notify:
    """
    A ``Notify`` object captures the basic configuration of how a notification should be handled.
    This includes the configuration of the SMTP connection to send emails which is either specified
    at runtime or loaded from the effective ``.pytb.config`` files ``notify`` section.

    The methods :meth:`when_done`, :meth:`every` and :meth:`when_stalled` are reenterable
    context managers. Thus a single ``Notify`` object can be reused at several places and 
    different context-managers can be reused in the same context.

    :param email_addresses: a list of email addresses. Each entry is a seperate recipient of 
        the notification send by this ``Notify``
    :param smtp_host: The SMTP servers address used to send the notifications
    :param smtp_port: The TCP port of the SMTP server
    :param smtp_ssl: Whether or not to use SSL for the SMTP connection

    All parameters are initialized from the effective ``.pytb.config`` if they are passed ``None``
    """

    def __init__(
        self, email_addresses=None, smtp_host=None, smtp_port=None, smtp_ssl=None
    ):
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        notify_config = current_config["notify"]
        if email_addresses is None:
            email_addresses = notify_config.getlist("email_addresses")

        if smtp_host is None:
            smtp_host = notify_config.get("smtp_host")

        if smtp_port is None:
            smtp_port = notify_config.getint("smtp_port")

        if smtp_ssl is None:
            smtp_ssl = notify_config.getboolean("smtp_ssl")

        if len(email_addresses) == 0:
            self._logger.warn(
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

    @contextmanager
    def when_done(self, message, only_if_error=False, capture_output=True):
        """
        Create a context that, when exited, will send notifications. If an unhandled exception
        is raised during execution, a notification on the failure of the execution is sent.
        If the context exits cleanly, a notification is only sent if ``only_if_error`` is set to ``False``

        By default, all output to the ``stdio`` and ``stderr`` streams is captured and sent in the notification.
        If you expect huge amounts of output during the execution of the monitored code, you can
        disable the capturing with the ``capture_output`` parameter.

        :param message: A short description of the monitored block. Used as the subject of the notification
        :param only_if_error: if the context manager exits cleanly, do not send any notifications
        :param capture_output: capture all output to the ``stdout`` and ``stderr`` stream and append it
            to the notification
        """
        self._logger.info(f"entering when done context")

        # we need to go 2 frames up because the direct parent is the contextmanagers ``__enter__`` method`
        caller_frame = inspect.currentframe().f_back.f_back

        output_buffer = StringIO()
        output_handler = (
            mirrored_stdstreams(output_buffer) if capture_output else nullcontext()
        )

        exception = None

        try:
            with output_handler:
                yield
        except Exception as e:
            exception = e

        output = output_buffer.getvalue()

        if exception is None and only_if_error:
            self._logger.info(
                f"Notification context left without error. Not firing notification"
            )
            return
        elif exception is not None:
            self.send_error(message, output, exception, caller_frame)
            raise exception
        else:
            self.send_success(message, output, caller_frame)

    def every(self, interval):
        pass

    def when_stalled(self, timeout):
        pass

    def send_success(self, message, output_buffer, caller_frame):
        print(message, output_buffer, caller_frame)

    def send_error(self, message, output_buffer, exception, caller_frame):
        print(message, output_buffer, exception, caller_frame)

    def _send_notification(self, messages):
        if self.smtp_class is not None:
            try:
                with self.smtp_class(self.smtp_host, self.smtp_port) as smtp:
                    for message in messages:
                        self._logger.info(f"sending message to {message['To']}")
                        smtp.send_message(message)
            except Exception as e:
                # we do not want to disrupt the user program if we fail to send the message
                self._logger.exception(f"error during sending of notification", e)
                pass
