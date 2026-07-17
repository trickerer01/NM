# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import os
import pathlib
import sys
from typing import BinaryIO

from .config import Config
from .defs import PREFIX, Quality
from .logger import Log
from .rex import re_media_filename

__all__ = ('FileLock', 'FileLockError', 'try_rename')


class FileLockError(Exception):
    pass


class FileLock:
    _opened_file_nondeletable = sys.platform.startswith('win')

    def __init__(self, filepath: os.PathLike | str) -> None:
        if Config.lock_files:
            fpath = pathlib.Path(filepath)
            self._lockpath = self.make_lock_path(fpath)
        else:
            self._lockpath = pathlib.Path()
        self._lockfile: BinaryIO | None = None

    @staticmethod
    def is_available() -> bool:
        return FileLock._opened_file_nondeletable

    @staticmethod
    def make_lock_path(filepath: pathlib.Path) -> pathlib.Path:
        if f_match := re_media_filename.fullmatch(filepath.name):
            f_id = f_match.group(1)
            f_quality = f'_{Quality(f_match.group(2))}' if f_match.group(2) else ''
            return filepath.with_name(f'{PREFIX}{f_id}{f_quality}.lock')
        return filepath.with_name(f'{filepath.name}.lock')

    async def __aenter__(self) -> FileLock:
        if Config.lock_files:
            try:
                # try to remove existing lock if previous run had its process forcefully terminated
                # raises PermissionError if file exists and is busy
                self._lockpath.unlink(missing_ok=True)
                self._lockpath.parent.mkdir(parents=True, exist_ok=True)
                # open in exclusive mode (create file)
                # raises FileExistsError if file already exists
                Log.trace(f'Locking {self._lockpath.as_posix()}...')
                self._lockfile = open(self._lockpath, 'bx')
            except OSError:
                raise FileLockError
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if Config.lock_files:
            if self._lockpath.is_file():
                if self._lockfile:
                    self._lockfile.close()
                    self._lockfile = None
                self._lockpath.unlink(missing_ok=True)


async def try_rename(oldpath: str, newpath: str, do_lock=False) -> bool:
    if oldpath == newpath:
        return True

    def _do_rename() -> None:
        os.makedirs(newpath_folder, exist_ok=True)
        os.rename(oldpath, newpath)

    try:
        newpath_folder = os.path.split(newpath.strip('/'))[0]
        if do_lock:
            async with FileLock(oldpath):
                _do_rename()
        else:
            _do_rename()
        return True
    except Exception:
        return False

#
#
#########################################
