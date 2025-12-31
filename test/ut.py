#!/usr/bin/env python3

import subprocess as sp
import sys
import tempfile as tmp
import unittest

from pathlib import Path

git_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(git_dir))
import pypkg

def run(*cmd):
    return sp.run([str(c) for c in cmd], stdout=sp.PIPE, stderr=sp.PIPE)

def test_pkg(pkg):
    with tmp.TemporaryDirectory() as tmp_dir:
        pkg_file = Path(tmp_dir) / 'tmp.py'
        pkg = pypkg.Pkg(git_dir / pkg)
        pkg.write_pkg(pkg_file)
        pkg_file.chmod(0o777)
        return run(pkg_file)


class TestRunPackages(unittest.TestCase):
    def test_hello_world(self):
        ret = test_pkg('test/hello_world/hello_world.py')
        self.assertEqual(ret.returncode, 0)
        self.assertEqual(ret.stdout, b'hello world\n')

    def test_hello_other_world(self):
        ret = test_pkg('test/hello_other_world/hello.py')
        self.assertEqual(ret.returncode, 0)
        self.assertEqual(ret.stdout, b'hello from other\n')

    def test_pandas_fail(self):
        ret = test_pkg('test/pandas_fail/main.py')
        self.assertNotEqual(ret.returncode, 0)
        self.assertTrue(b"No module named 'pandas'" in ret.stderr)

    def test_pandas_hello(self):
        ret = test_pkg('test/pandas_hello/main.py')
        self.assertEqual(ret.returncode, 0)
        self.assertTrue(b'Earthly Hello' in ret.stdout)
        self.assertTrue(b'Marshian Hello' in ret.stdout)

if __name__ == '__main__':
    unittest.main()
