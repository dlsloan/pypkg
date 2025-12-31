#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import argparse
import base64
import hashlib
import re
import shutil
import subprocess as sp
import sys
import typing as t
import venv
import zlib

from pathlib import Path

pypkg_dir = Path('~/.pypkg').expanduser().resolve(strict=False)

src_dir = Path(__file__).resolve().parent
pypkg_base = src_dir / 'pypkg_base.py'

def exception_hook(exc_type, exc_value, tb):
    print(f"{exc_type.__name__}, Message: {exc_value}", file=sys.stderr)
    local_vars = {}
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        name = tb.tb_frame.f_code.co_name
        line_no = tb.tb_lineno
        print(f"  {filename}:{line_no}, in {name}", file=sys.stderr)

        local_vars = tb.tb_frame.f_locals
        tb = tb.tb_next

sys.excepthook = exception_hook

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
        for line in self.tail:
            yield line + '\n'

    def write_pkg(self, file: Path):
        with file.open('w') as f:
            for line in self.dump_lines():
                f.write(line)


head, tail = pypkg_base.read_text().split('#INSERT_APP_DATA\n')
Pkg.head = head.split('\n')[:-1]
Pkg.tail = tail.split('\n')[:-1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root_doc', type=Path)
    args = parser.parse_args()
    pkg = Pkg(args.root_doc)
    for line in pkg.dump_lines():
        print(line, end='')
