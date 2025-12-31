#!/usr/bin/env python3

# Note: this is not a sandbox against malicious code, it can messed with quite easily

import base64
import os
import sys
import subprocess as sp
import tempfile
import venv
import zlib

from pathlib import Path

#INSERT_APP_DATA

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp_dir:
        builder = venv.EnvBuilder(clear=True, with_pip=True)
        base = Path(tmp_dir)
        venv_dir = base / 'venv'
        venv_dir.mkdir(parents=True)
        builder.create(venv_dir)
        venv_exe = venv_dir / 'bin/python3'
        src_dir = base / 'src'
        src_dir.mkdir()
        for file_name in files:
            file_path = src_dir / file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(zlib.decompress(base64.b64decode(files[file_name]['b64zlib_data'])))
            file_path.chmod(files[file_name]['chmod'])
        for dep in deps:
            ret = sp.run([str(venv_exe), '-m', 'pip', 'install', '--no-input', dep], stderr=sp.PIPE, stdout=sp.PIPE)
            if ret.returncode:
                print(ret.stderr.decode(), file=sys.stderr, end='', flush=True)
                exit(ret.returncode)
        ret = sp.run([str(venv_exe), src_dir / exec_root] + sys.argv[1:])

    exit(ret.returncode)
