#!/usr/bin/env python3

import argparse
import subprocess as sp

from pathlib import Path

git_dir = Path(__file__).resolve().parents[1]

def cmd_check(args):
    if args.verbose > 0:
        print('checking')

    ut_path = git_dir / 'test/ut.py'
    cmd = [ut_path, '-f']
    if args.verbose > 0:
        cmd += ['-' + 'v' * args.verbose]
    ret = sp.run([str(c) for c in cmd])
    if ret.returncode:
        exit(ret.returncode)

def cmd_install(args):    
    if args.verbose > 0:
        print('installing')

    rel_script_path = '../../.bin/pre-commit.py'
    hooks_dir = git_dir / '.git/hooks'
    hook_link = hooks_dir / 'pre-commit'

    if args.dry_run or args.verbose > 0:
        print(f"{hook_link} -> {rel_script_path}")
    
    if not args.dry_run:
        if hook_link.exists():
            hook_link.unlink()
        hook_link.symlink_to(rel_script_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.set_defaults(func=cmd_check)
    subparsers = parser.add_subparsers()

    check_parser = subparsers.add_parser('check')
    check_parser.set_defaults(func=cmd_check)

    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--dry-run', '-d', action='store_true')
    install_parser.set_defaults(func=cmd_install)

    args = parser.parse_args()
    args.func(args)
