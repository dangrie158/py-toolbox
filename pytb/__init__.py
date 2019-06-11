from .config import current_config
from .importlib import NoModuleCacheContext, NotebookLoader
from .rdb import install_hook as install_rdb

__all__ = ["io", "importlib", "config", "rdb", "init"]

_initialized = False

def init(verbose=True):
    """
    initialize the toolbox-subsystems using the current configuration

    :param verbose: print what this function is setting up
    """
    global _initialized
    
    if _initialized:
        raise RuntimeError('pytb toolkit is already initialized')
    
    config = current_config["init"]

    output = print if verbose else lambda x: None

    if config.getboolean('disable_module_cache'):
        output("entering global pytb.NoModuleCacheContext")
        NoModuleCacheContext().__enter__()
    else:
        output("'disable_module_cache' not set, skipping global context")

    if config.getboolean("install_notebook_loader"):
        output("installing NotebookLoader into 'sys.meta_path'")
        NotebookLoader.install_hook()
    else:
        output("'install_notebook_loader' not set, skipping installation of hook")

    if config.getboolean("install_rdb_hook"):
        output("installing RDB as default debugger in 'sys.breakpointhook'")
        install_rdb()
    else:
        output("'install_rdb_hook' not set, skipping installation of hook")
        
    _initialized = True