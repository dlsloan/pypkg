#!/usr/bin/env python3

import os
import subprocess as sp
import sys
import tempfile as tmp
import unittest

from pathlib import Path

git_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(git_dir))
import ctrace
import pypkg

class TestRunPackages(unittest.TestCase):
    @classmethod
    def run_cmd(cls, *cmd):
        return sp.run([str(c) for c in cmd], env=cls.env, stdout=sp.PIPE, stderr=sp.PIPE)

    @classmethod
    def check_pkg(cls, pkg, *, strict=True, print_err=True):
        with tmp.TemporaryDirectory() as tmp_dir:
            pkg_file = Path(tmp_dir) / 'tmp.py'
            pkg = pypkg.Pkg(git_dir / pkg)
            pkg.write_pkg(pkg_file)
            pkg_file.chmod(0o777)
            if strict:
                try:
                    env = dict(cls.env)
                    env['PYPKG_VENV_BASE'] = Path('~/.pypkg/test-venv').expanduser()
                    pkg.lint(env=env)
                except sp.CalledProcessError as err:
                    if print_err:
                        print('\n' + err.stderr.decode(), file=sys.stderr, end='')
                    raise
            return cls.run_cmd(pkg_file)

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tmp.TemporaryDirectory()
        cls.env = dict(os.environ)
        cls.env['PYPKG_VENV_BASE'] = cls.tmp_dir.name

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'tmp_dir'):
            cls.tmp_dir.cleanup()
            del cls.tmp_dir

    def assertRetZero(self, ret):
        b = '-' * 80
        self.assertEqual(ret.returncode, 0, f"\n{b}\nstderr:\n{ret.stderr.decode()}\n{b}\n")

    def test_hello_world(self):
        ret = self.check_pkg('test/hello_world/hello_world.py')
        self.assertRetZero(ret)
        self.assertEqual(ret.stdout, b'hello world\n')

    def test_hello_other_world(self):
        ret = self.check_pkg('test/hello_other_world/hello.py')
        self.assertRetZero(ret)
        self.assertEqual(ret.stdout, b'hello from other\n')

    def test_pandas_fail(self):
        ret = self.check_pkg('test/pandas_fail/main.py', strict=False)
        self.assertNotEqual(ret.returncode, 0)
        self.assertTrue(b"No module named 'pandas'" in ret.stderr)

    def test_pandas_hello(self):
        ret = self.check_pkg('test/pandas_hello/main.py')
        self.assertRetZero(ret)
        self.assertTrue(b'Earthly Hello' in ret.stdout)
        self.assertTrue(b'Marshian Hello' in ret.stdout)

    def test_mypy_fail(self):
        with self.assertRaises(sp.CalledProcessError):
            self.check_pkg('test/mypy_fail/main.py', print_err=False)

if __name__ == '__main__':
    unittest.main()
