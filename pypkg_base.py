#!/usr/bin/env python3

# Note: this is not a sandbox against malicious code, it can messed with quite easily

import base64
import contextlib
import hashlib
import os
import shutil
import sys
import subprocess as sp
import tempfile
import time
import venv
import zlib

from pathlib import Path

#INSERT_APP_DATA

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as tmp_dir:
        with dep_venv(deps) as venv:
            base = Path(tmp_dir)
            src_dir = base / 'src'
            src_dir.mkdir()
            for file_name in files:
                file_path = src_dir / file_name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(zlib.decompress(base64.b64decode(files[file_name]['b64zlib_data'])))
                file_path.chmod(files[file_name]['chmod'])
            ret = venv.runpy(src_dir / exec_root, sys.argv[1:])

    exit(ret.returncode)
