import doctest
import unittest

import pytb.itertools

suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.itertools))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
