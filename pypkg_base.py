#!/usr/bin/env python3

# Note: this is not a sandbox against malicious code, it can messed with quite easily
#INSERT_APP_DATA

import base64
import sys
import tempfile
import zlib

from pathlib import Path

if __name__ == '__main__':
    with dep_venv(deps) as venv:
        if len(sys.argv) > 1 and sys.argv[1] == '--install-deps-only':
            exit(0)
        with tempfile.TemporaryDirectory() as tmp_dir:
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
