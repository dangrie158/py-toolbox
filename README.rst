PyTb (Python Toolbox)
=====================

This is a collection of useful snippets I regularly find myself to use during prototyping.

Installation
------------

via pip:

``pip install py-toolbox``

or via distutils::

    git clone https://github.com/dangrie158/py-toolbox.git pytb
    cd pytb
    python setup.py install

Usage examples
--------------

**Redirecting output streams**

The ``io`` Module offers function to temporarly redirect or mirror ``stdout`` and ``stderr`` streams to a file

Stream redirection:

>>> from pytb.io import redirected_stdout
>>> with redirected_stdout('stdout.txt'):
...     print('this string will be written to stdout.txt and not to the console') 

**Stream mirroring**

>>> from pytb.io import mirrored_stdstreams
>>> with mirrored_stdstreams('alloutput.txt'):
...     print('this string will be written to alloutput.txt AND to the console') 

**Importing Jupyter-Notebooks as python modules**

>>> from pytb.importlib import no_module_cache, NotebookLoader
>>> NotebookLoader().install()
>>> import my.Notebook # will try to import the Notebook in './my/Notebook.ipynb'

NotebookLoaders can also be used as ContextManagers to only temporarly affect module loading and automatically remove the loader hook when exiting the context.

>>> from pytb.importlib import no_module_cache, NotebookLoader
>>> NotebookLoader():
...     import my.Notebook # will load the notebook
>>> import my.Notebook # will fail if there is no package named 'my'

**Automatically reload modules and packages when importing**

Use a ``NoModuleCacheContext`` to force reloading of modules that are imported. An instance of the ContextManager is available as ``pytb.importlib.no_module_cache``

>>> from pytb.importlib import no_module_cache, NotebookLoader
>>> NotebookLoader().install()
>>> import my.Notebook # load the module if it was not previously loaded
>>> with no_module_cache:
...     import my.Notebook # force reevaluation of the module (will execute all code again)
