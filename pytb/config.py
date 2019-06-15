import sys
import configparser
import logging
from pathlib import Path

"""
This module handles the .pytb.conf files
"""


class Config(configparser.ConfigParser):
    """
    Provides functionality to load a hierarchy of ``.pytb.config`` files.

    :param verbose: output debugging information including the paths
        that will be checked for config files as well as all files that
        are actually parsed
    """

    defaults = {
        "init": {
            "disable_module_cache": False,
            "install_notebook_loader": False,
            "install_rdb_hook": False,
        },
        "rdb": {
            "port": 8268,
            "bind_to": "0.0.0.0",
            "host": "127.0.0.1",
            "patch_stdio": True,
        },
        "module_cache": {"non_reloadable_packages": []},
        "notify": {
            "email_addresses": [],
            "smtp_host": "127.0.0.1",
            "smtp_port": 25,
            "smtp_ssl": False,
            "sender": "",
        },
    }
    """
    Set of default fallback values for all config settings
    """

    config_file_name = ".pytb.conf"
    """
    filename of config files
    """

    default_config_file = Path(__file__).parents[1] / config_file_name
    """
    The loaction of the default config file (in the root of the package)
    """

    @staticmethod
    def get_config_file_locations():
        """
        Get a list of possible configuration file paths by starting at the 
        current working directory and add all parent paths until the root directory is reached

        The default config file location is always the first path in the list.
        More specific configuration files should appear later in the list (from unspecific to more specific) 
        """
        # start at the current working directory
        directory = Path.cwd()
        config_paths = []
        while True:
            # potential config file in this directory
            config_file = directory / Config.config_file_name

            config_paths.append(config_file)

            # break if we reched the root directory
            if directory == Path(directory.root):
                break

            # move to the next parent directory
            directory = directory.parent

        # always append the default config file location
        config_paths.append(Config.default_config_file)
        return list(reversed(config_paths))

    def __init__(self, verbose=False):
        super().__init__()
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        if verbose:
            self._logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setLevel(logging.INFO)
            self._logger.addHandler(handler)

        self.reload()

    def reload(self):
        """
        load the configuration by initialising the default values from `Config.defaults` and then
        traversing all possible configuration files overwriting all newly found values
        """
        self.read_dict(Config.defaults)

        potential_config_files = Config.get_config_file_locations()
        self._logger.info(f"looking for config files in {potential_config_files}")

        files_loaded = self.read(potential_config_files)
        self._logger.info(f"loaded config from {files_loaded}")

    def getlist(self, *args, **kwargs):
        """
        get a list of values that are seperated by a newline character
        
        .. testsetup:: *

            from pytb.config import Config

        .. doctest::

            >>> config = Config()
            >>> config.read_string(\"""
            ...     [test]
            ...     list=a
            ...         b
            ...         c
            ...     \""")
            >>> config.getlist('test', 'list')
            ['a', 'b', 'c']

        """
        value = self.get(*args, **kwargs)
        # split at newlines and filter empty lines
        return [entry for entry in value.split("\n") if entry]


current_config = Config()
"""
An instance of config that is automatically initialized when importing the module
"""
