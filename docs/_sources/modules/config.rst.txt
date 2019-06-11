------------------
pytb.config module
------------------

*********************
Configure the Toolkit
*********************

Some modules use a configuration based on a config-file hierarchy.
This hierarchy starts in the current working directory moving to
parent folders until the root of the filesystem is reached.

The hierarchy is then traversed in reverse order and in each folder,
a file named ``.pytb.conf`` is loaded if available. The API docs for the
module reference when a configuration is used. The function of the config
parameters is documented in the `Default Config`_

**************
Default Config
**************

The pytb package provides a config file with sane default values
that should work in most cases. The file is loaded as first file
overwriting the hard-coded defaults in the :class:`pytb.config.Config` class
but being overwritten by any more-specific config file in the lookup hierarchy.

.. literalinclude:: ../../.pytb.conf
   :language: ini

*****************
API Documentation
*****************

.. automodule:: pytb.config
    :members:
    :show-inheritance:
