import doctest
import unittest

from io import StringIO
import sys
import tempfile

import pytb.io


class TestTeeManifold(unittest.TestCase):
    def test_tee_piece(self):
        file1, file2, file3 = StringIO(), StringIO(), StringIO()
        tee_piece = pytb.io.Tee(file1, file2, file3)
        tee_piece.write("test")

        self.assertEqual(file1.getvalue(), "test")
        self.assertEqual(file2.getvalue(), "test")
        self.assertEqual(file3.getvalue(), "test")

    def test_tee_piece_closes_files(self):
        file1, out, err = StringIO(), sys.__stdout__, sys.__stderr__
        tee_piece = pytb.io.Tee(file1, out, err)
        tee_piece.close()

        self.assertTrue(file1.closed)
        self.assertFalse(out.closed)
        self.assertFalse(err.closed)


class TestIORedirection(unittest.TestCase):
    def test__permissive_open_does_not_close_unopened(self):
        outfile = StringIO()
        with pytb.io._permissive_open(outfile) as file:
            self.assertFalse(file.closed)
        self.assertFalse(file.closed)

    def test__permissive_open_does_close_stringfile(self):
        outfile = tempfile.NamedTemporaryFile("w")
        with pytb.io._permissive_open(outfile.name, "w+") as file:
            self.assertFalse(file.closed)
        self.assertTrue(file.closed)

    def test__redirect_stream(self):
        outfile = StringIO()
        with pytb.io._redirect_stream(outfile, sys, "stdout"):
            print("stdout")

        with pytb.io._redirect_stream(outfile, sys, "stderr"):
            print("stderr", file=sys.stderr)
        self.assertEqual(outfile.getvalue(), "stdout\nstderr\n")

    def test__redirect_stream_restores_original_state(self):
        old_stdout = sys.stdout
        with pytb.io._redirect_stream(sys.stderr, sys, "stdout"):
            self.assertNotEqual(sys.stdout, old_stdout)
        self.assertEqual(sys.stdout, old_stdout)

    def test_mirrored_stdstreams(self):
        outfile, tmp_stdout, tmp_stderr = StringIO(), StringIO(), StringIO()
        with pytb.io.redirected_stdstreams(outfile):
            sys.stdout = pytb.io.Tee(tmp_stdout, sys.stdout)
            sys.stderr = pytb.io.Tee(tmp_stderr, sys.stderr)
            print("stdout")
            print("stderr", file=sys.stderr)

        self.assertEqual(tmp_stdout.getvalue(), "stdout\n")
        self.assertEqual(tmp_stderr.getvalue(), "stderr\n")

        self.assertEqual(outfile.getvalue(), "stdout\nstderr\n")


suite = unittest.TestSuite()
suite.addTest(doctest.DocTestSuite(pytb.io))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
