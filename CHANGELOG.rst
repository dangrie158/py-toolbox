*********
Changelog
*********

0.4.6
*****

- added on_iteration_of method to notification module
- removed 3.8 and nightly python versions from travis build bacause those
    versions are broken for pylint
- added type parameters to all modules and mypy to check types statically
- fixed error in _run_mainsave contextmanager in RDB module
- added pylint for static code analysis as build step and refactored code to
    pass analysis

0.4.5
*****

- fixed an error when importing importlib while no ipython is available
- updated dev requirements
- enabled automated CI with travis

0.4.4
*****

- added ``now()`` method to Notifiers to allow manually sending notifications

0.4.3
*****

- Added CHANGELOG to ditribution files

0.4.2
*****

- Fixed error when reading the "email_addresses" config option in CLI command
- Added dummy frame for code block display when using notification module via
    CLI
- Added automatic version detection in setup.py read from CHANGELOG

0.4.1
*****

- Fixed error when reading "use_ssl" config option in via-email CLI command

0.4.0
*****

- Added Notification Module for long running tasks
- Added CLI for Notification Module
- Added Documentation for Notification Module and CLI
- Switched to readthedocs.com for documentation hosting

0.3.0
*****

- Added Remote Debugger with CLI interface
- Added Documentation for Remote Debugger

0.2.3
*****

- Fixed an error during Notebook Transformation
- Added max_depth parameter for NoModuleCache

0.2.2
*****

- Added support for Input Transformation with Jupyter Magics in NotebookLoader

0.2.0
*****

- Added importing of Jupyter Notebooks as Modules via importlib

0.1.2
*****

- Basic I/O redirection

0.1.0
*****

- Initial Version
