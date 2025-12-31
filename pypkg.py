#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import argparse
import base64
import ctrace
import hashlib
import os
import re
import sys
import tempfile as tmp
import typing as t
import zlib

from pathlib import Path

from venv_helper import *

pypkg_dir = Path('~/.pypkg').expanduser().resolve(strict=False)

src_dir = Path(__file__).resolve().parent
pypkg_base = src_dir / 'pypkg_base.py'

def dump_file(path: Path):
    head = f"# {path.name} -"
    if len(head) < 80:
        head += '-' * (80 - len(head))
    tail = f"# {path.name} -"
    if len(tail) < 80:
        tail += '-' * (80 - len(tail))
    yield head + '\n'
    with path.open() as f:
        yield from f
    yield tail + '\n'

class Pkg:
    re_pragma_pip = re.compile(r'^\s*#pragma\s+\$pip\s+install\s+(\S+)(?:\s|$)')
    re_pragma_file = re.compile(r'^\s*#pragma\s+\$file\s+(?:"([^"]*)"|([^"\s]\S*))(?:\s|$)')

    files: dict[str, t.Tuple[bytes, int]]
    deps: dict[str, str|None]

    def __init__(self, target: Path):
        self.root = target.resolve().parent
        self.target = target.resolve().relative_to(self.root)
        self.files = {}
        self.deps = {}
        self.add_file(target)

    def add_file(self, path: Path):
        orig_path = path.resolve()
        path = orig_path.relative_to(self.root)
        if path in self.files:
            return

        file_data = orig_path.read_bytes()
        file_chmod = orig_path.stat().st_mode & 0o777
        self.files[path] = (file_data, file_chmod)
        if path.suffix.lower() == '.py':
            for line in file_data.decode().split('\n'):
                m = self.re_pragma_pip.match(line)
                if m:
                    self.add_dep(m.group(1))
                    continue
                m = self.re_pragma_file.match(line)
                if m:
                    if m.group(1) is not None:
                        file_path = Path(m.group(1))
                    else:
                        file_path = Path(m.group(2))

                    file_path = orig_path.parent / file_path
                    self.add_file(file_path)

    def add_dep(self, dep: str):
        if '<' in dep or '>' in dep:
            raise ValueError(f"Version ranges not supported: {dep}")
        if '=' in dep:
            pkg, ver = dep.split('==')
        else:
            pkg = dep
            ver = None

        if pkg in self.deps:
            if ver is None:
                return
            elif self.deps[pkg] is None:
                self.deps[pkg] = ver
            elif self.deps[pkg] != ver:
                raise ValueError(f"Multiple pip install version conflict: {dep} and {pkg}=={self.deps[pkg]}")
        else:
            self.deps[pkg] = ver

    def dump_lines(self):
        for line in self.head:
            yield line + '\n'
        indent = 0
        dep_pkgs = sorted(self.deps.keys())
        dep_hash = hashlib.sha256()
        yield "deps = [\n"
        indent += 2
        for pkg in dep_pkgs:
            ver = self.deps[pkg]
            if ver is None:
                dep = pkg
            else:
                dep = f"{pkg}=={ver}"
            dep_hash.update(dep.encode() + b"\n")
            yield ' ' * indent + str(dep.encode())[1:] + ",\n"
        indent -= 2
        yield ']\n'
        yield f"dep_hash = {str(dep_hash.hexdigest().encode())[1:]}\n"
        file_paths = sorted(self.files.keys())
        yield 'files = {\n'
        indent += 2
        files_hash = hashlib.sha256()
        for path in file_paths:
            data, chmod = self.files[path]
            files_hash.update(str(path).encode() + b"\n")
            files_hash.update(f"{len(data)}:".encode())
            files_hash.update(data)
            yield ' ' * indent + f"{str(str(path).encode())[1:]}: {{\n"
            yield ' ' * (indent + 2) + f"'b64zlib_data': {str(base64.b64encode(zlib.compress(data, level=zlib.Z_BEST_COMPRESSION)))[1:]},\n"
            yield ' ' * (indent + 2) + f"'sha256sum': '{hashlib.sha256(data).hexdigest()}',\n"
            yield ' ' * (indent + 2) + f"'chmod': {chmod},\n"
            yield ' ' * indent + '},\n'
        indent -= 2
        yield '}\n'
        yield f"files_hash = {str(files_hash.hexdigest().encode())[1:]}\n"
        yield f"exec_root = {str(str(self.target).encode())[1:]}\n"
        yield '\n'
        yield from dump_file(src_dir / 'venv_helper.py')
        yield from dump_file(src_dir / 'ctrace.py')
        for line in self.tail:
            yield line + '\n'

    def write_pkg(self, file: Path):
        with file.open('w') as f:
            for line in self.dump_lines():
                f.write(line)

    def dep_list(self):
        ret = []
        dep_pkgs = sorted(self.deps.keys())
        for pkg in dep_pkgs:
            ver = self.deps[pkg]
            if ver is None:
                dep = pkg
            else:
                dep = f"{pkg}=={ver}"
            ret.append(dep)
        return ret

    def lint(self, env=None):
        with tmp.TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            for file_name in self.files:
                data, chmod = self.files[file_name]
                path = tmp_dir / file_name
                path.write_bytes(data)
                path.chmod(chmod)
            with dep_venv(self.dep_list() + ['mypy'], env=env) as venv:
                for file_name in self.files:
                    if file_name.suffix.lower() == '.py':
                        path = tmp_dir / file_name
                        ret = venv.runpy('-m', 'mypy', '--strict', path, env=env, stdout=sp.PIPE, stderr=sp.PIPE)
                        if ret.returncode:
                            raise sp.CalledProcessError(ret.returncode, ret.args, stderr=ret.stdout)

head, tail = pypkg_base.read_text().split('#INSERT_APP_DATA\n')
Pkg.head = head.split('\n')[:-1]
Pkg.tail = tail.split('\n')[:-1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root_doc', type=Path)
    parser.add_argument('--no-lint', action='store_true')
    args = parser.parse_args()
    pkg = Pkg(args.root_doc)
    try:
        if not args.no_lint:
            pkg.lint()
    except sp.CalledProcessError as err:
        print(err.stderr.decode(), end='', file=sys.stderr, flush=True)
        exit(err.returncode)
    for line in pkg.dump_lines():
        print(line, end='')
