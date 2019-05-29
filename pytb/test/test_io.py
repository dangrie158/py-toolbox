import doctest
import unittest

import pytb.io

suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.io))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)