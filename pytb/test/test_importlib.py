import doctest
import unittest

import sys
import io

from pytb import importlib, test, io as pyio


class TestNotebookLoader(unittest.TestCase):
    def test_load_notebook(self):
        out = io.StringIO()
        with pyio.redirected_stdout(out):
            with importlib.NotebookLoader(), importlib.no_module_cache:
                import pytb.test.fixtures.TestNB
        self.assertEqual(out.getvalue(), "Hello from Notebook\n")

    def test_transform_ipython_magic(self):
        out = io.StringIO()
        with pyio.redirected_stdout(out):
            with importlib.NotebookLoader():
                import pytb.test.fixtures.IPython_TestNB
        self.assertEqual(out.getvalue(), "Hello from Notebook\r\nHello from Notebook\n")


class TestNoModuleCache(unittest.TestCase):
    def test_reload_on_import(self):

        from .fixtures import random_module

        rand_num_one = random_module.random_number
        with importlib.NoModuleCacheContext():
            from .fixtures import random_module

        rand_num_two = random_module.random_number
        self.assertNotEqual(rand_num_one, rand_num_two)

        with importlib.no_module_cache:
            from .fixtures import random_module

        rand_num_three = random_module.random_number
        self.assertNotEqual(rand_num_two, rand_num_three)


suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(importlib))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
