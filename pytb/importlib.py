"""
This module contains useful helper scripts regarding the loading of modules
"""

# pylint wrongly assumes imports to importlib regard this module
# instead of the builtin package, thus we need to disable some checks
import sys
import os
import io
import builtins
import logging
import importlib  # pylint: disable=import-self
from importlib.machinery import (  # pylint: disable=no-name-in-module, import-error
    ModuleSpec,
)
from contextlib import AbstractContextManager
from contextlib import suppress

from nbformat import read as read_notebook

with suppress(Exception):
    from IPython import get_ipython
    from IPython.core.interactiveshell import InteractiveShell

from pytb.config import current_config as pytb_config


class ModuleLoader(AbstractContextManager):
    """
    A abstract base class for a general module loader interface
    that can be dynamically installed and uninstalled from the ``sys.meta_path``

    Can be used as a context manager to automatically install the loader when entering the context
    and uninstall

    :param verbose: if True, prints attempts to find and load a module
    :param always_reload: if True, prints attempts to find and load a module

    .. testsetup:: *

        import sys
        from pytb.importlib import ModuleLoader

    .. doctest::

        >>> with ModuleLoader() as loader:
        ...     assert loader in sys.meta_path
        >>> assert loader not in sys.meta_path

    """

    def __init__(self, verbose=False):
        self._logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        if verbose:
            self._logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setLevel(logging.INFO)
            self._logger.addHandler(handler)

    def find_spec(self, fullname, path, target=None):
        # pylint: disable=unused-argument,missing-docstring
        # overwrite in child classes to do something sensible
        self._logger.info(f"looking for module {fullname} in path {path}")

    def create_module(self, spec):
        # pylint: disable=unused-argument,missing-docstring,no-self-use
        # return None to indicate default module creation semantics
        return None

    def exec_module(self, module):
        # pylint: disable=missing-docstring
        self._logger.info(f"loading module {module.__name__}")

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.uninstall()

    def install(self):
        """
        Install this loader into the metapath.

        :raises RuntimeError: If this loader is already installed

        .. doctest::

            >>> loader = ModuleLoader()
            >>> loader.install()
            >>> assert loader in sys.meta_path
            >>> loader.install()
            Traceback (most recent call last):
                ...
            RuntimeError: Loader was already installed.

        """
        if self in sys.meta_path:
            raise RuntimeError("Loader was already installed.")
        sys.meta_path.append(self)

    def uninstall(self):
        """
        Uninstall this loader from the meta_path.

        :raises RuntimeError: If this loader was never installed or was previously uninstalled

        .. doctest::

        >>> loader = ModuleLoader()
        >>> loader.install()
        >>> loader.uninstall()
        >>> assert loader not in sys.meta_path
        >>> loader.uninstall()
        Traceback (most recent call last):
            ...
        RuntimeError: Tried to uninstall loader that is not installed or was already uninstalled.

        """
        try:
            sys.meta_path.remove(self)
        except ValueError:
            raise RuntimeError(
                "Tried to uninstall loader that is not installed or was already uninstalled."
            )

    @classmethod
    def install_hook(cls):
        """
        Install an instance of the loader and return the instance

        .. doctest::

            >>> loader = ModuleLoader.install_hook()
            >>> assert loader in sys.meta_path
            >>> loader.uninstall()
            >>> assert loader not in sys.meta_path
        """
        loader = cls()
        loader.install()
        return loader


class NoModuleCacheContext(AbstractContextManager):
    """
    Contextmanager to temporarly disable module chaching

    While this context is active, every import statement will reevaluate the entire
    module and all modules imported by it.

    Excluded from the reloading are all modules in :attr:`sys.builtin_module_names`
    and some modules in the stdlib that do not like to be reloaded. The list of unreloadable
    modules is defined in :attr:`NoModuleCacheContext._no_reloadable_packages`

    An instance of this class is available as :attr:`no_module_cache`

    :param verbose: Print a list of modules that were reloaded for each import call

    .. doctest::

        >>> from pytb.importlib import NoModuleCacheContext, NotebookLoader
        >>> NotebookLoader().install()
        >>> with NoModuleCacheContext():
        ...     import pytb.test.fixtures.TestNB
        ...     import pytb.test.fixtures.TestNB
        Hello from Notebook
        Hello from Notebook
    """

    # it does not make much sense to reload built-ins. Additionally there
    # are some modules in the stdlib that do not like to be reloaded and
    # throw an error, so we exclude them here as they do not make sense
    # to live-reload them anyway
    _no_reloadable_packages = pytb_config.getlist(
        "module_cache", "non_reloadable_packages"
    )

    class CachlessImporter:
        """
        Callable wrapper class that handles the calls to ``__import__``
        in a way that effectively disables the module cache by reloading
        modules that are already loaded into ```sys.modules```
        """

        def __init__(self, import_fun, verbose, max_depth):
            self.import_fun = import_fun
            self.module_stack = []
            self.reloaded_modules_in_last_call = []
            self.max_depth = max_depth

            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
            if verbose:
                self._logger.setLevel(logging.INFO)
                handler = logging.StreamHandler(stream=sys.stdout)
                handler.setLevel(logging.INFO)
                self._logger.addHandler(handler)

        def __call__(self, name, globals=None, locals=None, fromlist=(), level=0):
            # pylint: disable=redefined-builtin,protected-access,too-many-arguments
            if level > 0:
                # relative import, add the package name to the module name
                package = importlib._bootstrap._calc___package__(  # pylint: disable=no-member
                    globals
                )
                fullname = importlib._bootstrap._resolve_name(  # pylint: disable=no-member
                    name, package, level
                )
            else:
                # absolute import
                fullname = name

            if fullname in self.module_stack:
                # early breakout skip reloading modules that were already
                # reloaded in this import call to avoid recursive loops
                return self.import_fun(name, globals, locals, fromlist, level)

            module_name = fullname.partition(".")[0]

            if (
                fullname not in self.reloaded_modules_in_last_call
                and module_name not in NoModuleCacheContext._no_reloadable_packages
            ):
                # reload the module itself first, as the children
                # in fromlist may need it already in sys.modules
                self.maybe_reload_module(fullname)
                if fromlist:
                    # reload all children from the partslist
                    for part in fromlist:
                        el_name = ".".join((fullname, part))
                        self.maybe_reload_module(el_name)

            # add the module name to the current call stack before calling the
            # original builtin as importing a module may itself import modules and
            # thus call this function
            self.module_stack.append(fullname)

            # resolve the module. use the the original builtin to handle all
            # the special cases easily
            module = self.import_fun(name, globals, locals, fromlist, level)

            # importing of the module done, pop it from the stack
            self.module_stack.remove(fullname)
            return module

        def maybe_reload_module(self, fullname):
            """
            Reload the module if it already is loaded into :attr:`sys.modules`
            and add the module to the list of reloaded modules in this call

            :param fullname: FQN of the module to reload
            """
            if fullname in sys.modules and (
                self.max_depth is None or len(self.module_stack) < self.max_depth
            ):
                self.reloaded_modules_in_last_call.append(fullname)
                importlib.reload(sys.modules[fullname])  # pylint: disable=no-member

        def flush_reload_stack(self):
            """
            Clear the list of reloaded modules in this call. If this instance is verbose,
            print the list of reloaded modules
            """
            self._logger.info(f"reloaded modules {self.reloaded_modules_in_last_call}")
            self.reloaded_modules_in_last_call.clear()

    def __init__(self, verbose=False, max_depth=None):
        self.is_verbose = verbose
        self._next_context_is_verbose = False
        self.max_depth = max_depth

        self.original_import_fun = None
        self.custom_import_fun = None

    def __enter__(self):
        verbosity = self._next_context_is_verbose or self.is_verbose
        self._next_context_is_verbose = False
        self.original_import_fun = builtins.__import__
        self.custom_import_fun = self.CachlessImporter(
            self.original_import_fun, verbosity, self.max_depth
        )
        builtins.__import__ = self.custom_import_fun

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.custom_import_fun.flush_reload_stack()
        builtins.__import__ = self.original_import_fun
        self.is_verbose = False

    def __call__(self, *args, verbose=False, **kwargs):
        self._next_context_is_verbose = verbose
        return self


# pylint: disable=invalid-name
no_module_cache = NoModuleCacheContext()
"""
An instance of :class:`NoModuleCacheContext` ready for use
"""


class NotebookLoader(ModuleLoader):
    """
    A :class:`ModuleLoader` that allows importing of jupyter Notebooks as python modules.

    .. doctest::

        >>> from pytb.importlib import NotebookLoader, no_module_cache
        >>> with NotebookLoader(), no_module_cache:
        ...     import pytb.test.fixtures.TestNB
        Hello from Notebook

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shell = (
            InteractiveShell.instance() if "InteractiveShell" in globals() else None
        )

    @staticmethod
    def _find_notebook(fullname, path):
        name = fullname.rsplit(".", 1)[-1]
        if not path:
            path = [""]

        for part in path:
            nb_path = os.path.join(part, name + ".ipynb")
            if os.path.isfile(nb_path):
                return nb_path
            # let import Notebook_Name find "Notebook Name.ipynb"
            nb_path = nb_path.replace("_", " ")
            if os.path.isfile(nb_path):
                return nb_path
        return None

    def find_spec(self, fullname, path, target=None):
        super().find_spec(fullname, path, target)

        nb_path = NotebookLoader._find_notebook(fullname, path)
        if nb_path is None:
            return None

        self._logger.info(f"Found notebook file {nb_path}")

        return ModuleSpec(fullname, self, origin=nb_path)

    def exec_module(self, module):
        super().exec_module(module)

        with io.open(  # pylint: disable=no-member
            module.__spec__.origin, "r", encoding="utf-8"
        ) as f:
            notebook = read_notebook(f, 4)

        if self.shell is not None:
            module.__dict__["get_ipython"] = get_ipython
            # extra work to ensure that magics that would affect the user_ns
            # actually affect the notebook module's namespace
            save_user_ns = self.shell.user_ns
            self.shell.user_ns = module.__dict__

        try:
            for cell in notebook.cells:
                if cell.cell_type == "code":
                    if self.shell is not None:
                        code = self.shell.input_transformer_manager.transform_cell(
                            cell.source
                        )
                    else:
                        code = cell.source

                    # run the code in them odule
                    # pylint: disable=exec-used
                    exec(code, module.__dict__)
        finally:
            if self.shell is not None:
                self.shell.user_ns = save_user_ns

        return module
