import doctest
import unittest

import sys

import pytb.importlib

class TestNoModuleCache(unittest.TestCase):
    def test_reload_on_import(self):

        from .fixtures import random_module
        rand_num_one = random_module.random_number
        with pytb.importlib.NoModuleCacheContext():
            from .fixtures import random_module

        rand_num_two = random_module.random_number
        self.assertNotEqual(rand_num_one, rand_num_two)

        with pytb.importlib.no_module_cache:
            from .fixtures import random_module
        
        rand_num_three = random_module.random_number
        self.assertNotEqual(rand_num_two, rand_num_three)

suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.importlib))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)