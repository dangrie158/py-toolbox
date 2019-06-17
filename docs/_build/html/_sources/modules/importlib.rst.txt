---------------------
pytb.importlib module
---------------------

*********************************************
Importing Jupyter-Notebooks as python modules
*********************************************

    >>> from pytb.importlib import no_module_cache, NotebookLoader
    >>> loader = NotebookLoader()
    >>> loader.install()
    >>> # will try to import the Notebook in './my/Notebook.ipynb'
    >>> import pytb.test.fixtures.Notebook
    >>> loader.uninstall()

NotebookLoaders can also be used as ContextManagers to only temporarly
affect module loading and automatically remove the loader hook when
exiting the context.

    >>> from pytb.importlib import no_module_cache, NotebookLoader
    >>> with NotebookLoader():
    ...     import pytb.test.fixtures.Notebook # will load the notebook
    >>> # next line will fail if there is no package named 'my'
    >>> import pytb.test.fixtures.Notebook

********************************************************
Automatically reload modules and packages when importing
********************************************************

This is especially useful in combination with a Notebook Loader.
You can simply run an import cell again to reload the Notebook Code from disk.

Use a ``NoModuleCacheContext`` to force reloading of modules that are imported.
An instance of the ContextManager is available as
``pytb.importlib.no_module_cache``.

Some packages can not be reloaded as they define a global state that does not
like to be created again. The default config defines a sane set of packages
that are ignored by the reloader.

    >>> from pytb.importlib import no_module_cache, NotebookLoader
    >>> loader = NotebookLoader().install()
    >>> # load the module if it was not previously loaded
    >>> import pytb.test.fixtures.Notebook
    >>> with no_module_cache:
    ...     # force reevaluation of the module (will execute all code again)
    ...     import pytb.test.fixtures.Notebook

*****************
API Documentation
*****************

.. automodule:: pytb.importlib
    :members:
    :show-inheritance:
