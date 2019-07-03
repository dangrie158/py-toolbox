"""
    This module contains a set of helpers for common Input/Output related tasks
"""
import sys
import textwrap
from io import StringIO
from typing import Any, TextIO, Union, Generator, cast
from contextlib import contextmanager


class Tee:
    """
    A N-ended T-piece (manifold) for File objects that supports writing.
    This is useful if you want to write to multiple files or file-like objects
    (e.g. ``sys.stdout``, ``sys.stderr``) simultaneously.

    .. testsetup:: *

        from pytb.io import *

    .. doctest::

        >>> import sys, io
        >>> file_like = io.StringIO()
        >>> combined = Tee(file_like, sys.stdout)
        >>> _ = combined.write('This is printed into a file and on stdout\\n')
        This is printed into a file and on stdout
        >>> assert file_like.getvalue() == 'This is printed into a file and on stdout\\n'
    """

    def __init__(self, *args: TextIO):
        """
        Instantiate a new manifold that connects all passed file-like objects' output streams

        :param *args: file-like objects to connect to the manifold
        """
        self._fds = args

    def write(self, text: str) -> int:
        """
        Write to the manifold which, in turn, writes to all connected output streams

        :param text: text to write to the manifold
        :return: the number of bytes written to the last stream in the Manifold
        """
        for stream in self._fds:
            written = stream.write(text)

        return written

    def flush(self) -> None:
        """
        Flush any buffers of all connected file output-streams
        """
        for stream in self._fds:
            stream.flush()

    def close(self) -> None:
        """
        Close all connected files

        This does avoid closing ``sys.__stdout__`` and ``sys.__stderr__``

        .. doctest::

            >>> import sys, io
            >>> file_like = io.StringIO()
            >>> combined = Tee(file_like, sys.__stdout__)
            >>> file_like.closed
            False
            >>> combined.close()
            >>> file_like.closed
            True
            >>> sys.stdout.closed
            False
        """
        for stream in self._fds:
            if stream not in [sys.__stderr__, sys.__stdout__]:
                stream.close()


AnyTextIOType = Union[str, TextIO, Tee]


@contextmanager
def _permissive_open(
    file: AnyTextIOType, mode: str = "r"
) -> Generator[TextIO, None, None]:
    """
    Contextmanager that acts like a call to ``open()``  but accepts also
    a already opened File object. If passed a string, the file is opened
    using a call to ``open()`` passing all additional parameters along.
    The file is automatically closed using ``File.close()`` after the
    context manager exits only if the file was also opened by a call to this function.

    .. doctest::

        >>> import io, tempfile
        >>> outfile = io.StringIO()
        >>> with _permissive_open(outfile) as file:
        ...     print(file.closed)
        False
        >>> file.closed
        False

    .. doctest::

        >>> outfile = tempfile.NamedTemporaryFile('w')
        >>> with _permissive_open(outfile.name, 'w+') as file:
        ...     print(file.closed)
        False
        >>> file.closed
        True
    """
    if isinstance(file, str):
        file_obj = cast(TextIO, open(file, mode))
    else:
        file_obj = cast(TextIO, file)

    try:
        yield file_obj
    finally:
        # close the file only if we opened it,
        # otherwise leave it open
        if isinstance(file, str):
            file_obj.close()


@contextmanager
def _redirect_stream(
    file: AnyTextIOType, module: Any, attr: str
) -> Generator[TextIO, None, None]:
    with _permissive_open(file, "w") as out:
        old = getattr(module, attr)
        setattr(module, attr, out)
        sys.stdout = out
        try:
            yield out
        finally:
            setattr(module, attr, old)


@contextmanager
def redirected_stdout(file: AnyTextIOType) -> Generator[TextIO, None, None]:
    """
    ContextManager that redirects stdout to a given file-like object
    and restores the original state when leaving the context

    :param file: string or file-like object to redirect stdout to.
                 If passed a string, the file is opened for writing and closed
                 after the contextmanager exits

    .. doctest::

        >>> import io
        >>> outfile = io.StringIO()
        >>> with redirected_stdout(outfile):
        ...     print('this is written to outfile')
        >>> assert outfile.getvalue() == 'this is written to outfile\\n'
    """
    with _redirect_stream(file, sys, "stdout") as redirected:
        yield redirected


@contextmanager
def redirected_stderr(file: AnyTextIOType) -> Generator[TextIO, None, None]:
    """
    Same functionality as ``redirect_stdout`` but redirects the stderr stram instead

    see :meth:`redirected_stdout`
    """
    with _redirect_stream(file, sys, "stderr") as redirected:
        yield redirected


@contextmanager
def redirected_stdstreams(file: AnyTextIOType) -> Generator[TextIO, None, None]:
    """
    redirects both output streams (``stderr`` and ``stdout``) to ``file``

    see :meth:`redirected_stdout`
    """
    with _redirect_stream(file, sys, "stdout") as _redirected_stdout:
        with _redirect_stream(_redirected_stdout, sys, "stderr") as _redirected_stderr:
            yield _redirected_stderr


@contextmanager
def mirrored_stdout(file: AnyTextIOType) -> Generator[TextIO, None, None]:
    """
    ContextManager that mirrors stdout to a given file-like object
    and restores the original state when leaving the context

    This is essentially using a ``Tee`` piece manifold to ``file`` and ``sys.stdout``
    as a parameter to ``redirected_stdout``

    :param file: string or file-like object to mirror stdout to.
                 If passed a string, the file is opened for writing and closed
                 after the contextmanager exits

    .. doctest::

        >>> import io
        >>> outfile = io.StringIO()
        >>> with mirrored_stdout(outfile):
        ...     print('this is written to outfile and stdout')
        this is written to outfile and stdout
        >>> assert outfile.getvalue() == 'this is written to outfile and stdout\\n'
    """
    with _permissive_open(file, "w") as out:
        tee_piece = Tee(sys.stdout, out)
        with redirected_stdout(tee_piece) as out:
            yield out


@contextmanager
def mirrored_stdstreams(file: AnyTextIOType) -> Generator[TextIO, None, None]:
    """
    Version of :meth:`mirrored_stdout` but mirrors ``stderr`` and ``stdout`` to file

    see :meth:`mirrored_stdout`
    """
    with _permissive_open(file, "w") as out:
        tee_piece_out = Tee(sys.stdout, out)
        with redirected_stdout(tee_piece_out):
            tee_piece_err = Tee(sys.stderr, out)
            with redirected_stderr(tee_piece_err):
                yield out


def render_text(text: str, maxwidth: int = -1) -> str:
    r"""
    Attempt to render a text like an (potentiall infinitely wide)
    terminal would.

    Thus carriage-returns move the cursor to the start of
    the line, so subsequent characters overwrite the previous.

    .. doctest::

        >>> render_text('asd\rbcd\rcde\r\nqwe\rert\n123', maxwidth=2)
        'cd\ne \ner\nt \n12\n3'

    :param text: Input text to render
    :param maxwidth: if > 0, wrap the text to the specified maximum length
        using the textwrapper library
    """
    # create a buffer for the rendered ouput text
    outtext = StringIO()
    for char in text:
        if char == "\r":
            # seek to one character past the last new line in
            # the current rednered text. This woks nicely because
            # rfind will return -1 if no newline is found this
            # this will seek to the beginning of the stream
            outtext.seek(outtext.getvalue().rfind("\n") + 1)

            # continue to the next character, dont write he carriage return
            continue
        elif char == "\n":
            # a newline moves the cursor to the end of he buffer
            # the newline itself is written below
            outtext.seek(len(outtext.getvalue()))

        # write he current character to the buffer
        outtext.write(char)

    rendered_text = outtext.getvalue()

    # connditionnally wrap the text after maxwidth characters
    if maxwidth > 0:
        rendered_text = textwrap.fill(rendered_text, maxwidth)
    return rendered_text
