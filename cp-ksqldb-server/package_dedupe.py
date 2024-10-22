#! /usr/bin/env python3
"""
Execute this script from inside a directory full of potentially duplicate
files.  It will check the shasum of every file recursively, saving the path
of the first copy in a dictionary, and symlinking subsequently found
duplicates back to that first copy.
"""

from hashlib import sha1
from os import walk
from os.path import relpath
from pathlib import Path
from typing import Dict
import logging

def shasum(pathname: Path) -> str:
    """Return the shasum for the contents of PATHNAME."""
    sha1sum = sha1()
    with pathname.open(mode='rb') as source:
        block = source.read(2**16)
        while len(block) != 0:
            sha1sum.update(block)
            block = source.read(2**16)
    return sha1sum.hexdigest()



def dedupe(path: Path):
# Keep track of every "first copy" of all files with the same shasum.
    sha2path: Dict[str, Path] = {}

    for dirname, _, filenames in walk(path):
        for filename in filenames:
            path = Path(dirname) / filename
            if path.is_symlink():
                # Executing the script again must be harmless.
                continue

            sha = shasum(path)
            if sha not in sha2path:
                # Record this PATH as the "first copy" with the given SHA.
                sha2path[sha] = path
            else:
                # Otherwise, replace this file with a symlink to the "first copy".
                orig = sha2path[sha]
                target = relpath(str(orig), str(path.parent))
                path.unlink()
                path.symlink_to(target)
                logging.info(f'DEDUP: ln -sf {target} {str(path)}')

