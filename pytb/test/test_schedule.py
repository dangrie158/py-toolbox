import doctest
import unittest

import pytb.itertools
from functools import partial


class TestNamedProduct(unittest.TestCase):
    def test_does_safcopy(self):
        def test(a, b):
            pass

        a = list(
            pytb.itertools.named_product(
                {"x": partial(test, a=2), "y": [1, 2]}, 1, safe_copy=True
            )
        )
        self.assertIsNot(a[0]["x"], a[1]["x"])

        a[0]["x"].keywords["a"] = 42
        self.assertEqual(a[0]["x"].keywords["a"], 42)
        self.assertEqual(a[1]["x"].keywords["a"], 2)


suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.itertools))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
