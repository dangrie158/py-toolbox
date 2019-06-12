import doctest
import unittest

import pytb.config

suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.config))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
