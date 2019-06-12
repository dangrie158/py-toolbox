import sys
import inspect
import logging

from .config import current_config
from .importlib import NoModuleCacheContext, NotebookLoader
from .rdb import install_hook as install_rdb

_initializer_frame = None


def init(verbose=True, reinitalisation_attempt_ok=False):
    """
    initialize the toolbox-subsystems using the current configuration

    :param verbose: print what this function is setting up
    :param reinitalisation_attempt_ok: If False, a reinitialization attempt will 
        raise a ``RuntimeError`` otherwise a reinitialization attempt is simply ignored.
        If verbose is true, this will also log a warning
    """
    global _initializer_frame

    _logger = logging.getLogger(__name__)
    if verbose:
        _logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.INFO)
        _logger.addHandler(handler)
    if _initializer_frame:
        reinitialization_message = f"pytb toolkit was already initialized in {_initializer_frame.f_code.co_filename}:{_initializer_frame.f_code.co_name} on line {_initializer_frame.f_lineno}"
        if reinitalisation_attempt_ok:
            _logger.warn(
                f"skipping initialization of toolbox. {reinitialization_message}"
            )
            return
        else:
            raise RuntimeError(reinitialization_message)

    config = current_config["init"]

    if config.getboolean("disable_module_cache"):
        _logger.info("entering global pytb.NoModuleCacheContext")
        NoModuleCacheContext().__enter__()
    else:
        _logger.info("'disable_module_cache' not set, skipping global context")

    if config.getboolean("install_notebook_loader"):
        _logger.info("installing NotebookLoader into 'sys.meta_path'")
        NotebookLoader.install_hook()
    else:
        _logger.info("'install_notebook_loader' not set, skipping installation of hook")

    if config.getboolean("install_rdb_hook"):
        _logger.info("installing RDB as default debugger in 'sys.breakpointhook'")
        install_rdb()
    else:
        _logger.info("'install_rdb_hook' not set, skipping installation of hook")

    # store the calling frame to output a useful message when attempting to reinitialize the toolkit
    _initializer_frame = inspect.currentframe().f_back
