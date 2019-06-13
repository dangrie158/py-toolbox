import doctest
import unittest

import pytb.notification

suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.notification))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
