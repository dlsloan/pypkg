import contextlib
import hashlib
import os
import subprocess as sp
import time
import venv

from pathlib import Path

class VenvHandle:
    def __init__(self, venv_path):
        self.venv_path = Path(venv_path).resolve()
        self.exe_path = self.venv_path / 'bin/python3'

    def runpy(self, *cmd, **kwarg):
        cmd_list = [self.exe_path]
        cmd_list += list(cmd)
        return sp.run([str(c) for c in cmd_list], **kwarg)

@contextlib.contextmanager
def dep_venv(deps, timeout: int=60, env=None):
    sha = hashlib.sha256()
    for dep in deps:
        sha.update(dep.encode() + b'\n')
    checksum = sha.hexdigest()

    if env is None:
        env = dict(os.environ)
    if 'PYPKG_VENV_BASE' in env:
        pypkg_env_base = Path(env['PYPKG_VENV_BASE']).resolve()
    else:
        pypkg_env_base = Path('~/.pypkg/venv').expanduser().resolve()

    pypkg_env = pypkg_env_base / f".{checksum}"
    pypkg_env_link = pypkg_env_base / checksum

    start = time.time()
    while not pypkg_env_link.exists():
        try:
            try:
                pypkg_env.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                if time.time() - start > timeout:
                    raise TimeoutError()
                time.sleep(1)
                continue
            builder = venv.EnvBuilder(clear=True, with_pip=True)
            builder.create(pypkg_env)
            h = VenvHandle(pypkg_env)
            for dep in deps:
                ret = h.runpy('-m', 'pip', 'install', '--no-input', dep, stderr=sp.PIPE, stdout=sp.PIPE, env=env)
                if ret.returncode:
                    shutil.rmtree(pypkg_env)
                    print(ret.stderr.decode(), file=sys.stderr, end='', flush=True)
                    exit(ret.returncode)
            pypkg_env_link.symlink_to(pypkg_env.name)
            break
        except:
            try:
                shutil.rmtree(pypkg_env)
            except:
                pass
            raise

    yield VenvHandle(pypkg_env_link)
