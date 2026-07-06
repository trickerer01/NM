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
from collections.abc import MutableSequence
from typing import BinaryIO

from .config import Config
from .defs import DEFAULT_EXT, PREFIX, Quality
from .iinfo import VideoInfo
from .logger import Log
from .rex import re_media_filename
from .util import normalize_path

__all__ = (
    'FileLock',
    'FileLockError',
    'file_already_exists',
    'file_already_exists_arr',
    'prefilter_existing_items',
    'register_new_file',
    'try_rename',
    'unregister_unfinished_file',
)

_opened_file_nondeletable = sys.platform.startswith('win')
_found_filenames_dict: dict[str, list[str]] = {}
_media_matches_cache: dict[str, tuple[str, Quality]] = {}


class FileLockError(Exception):
    pass


class FileLock:
    def __init__(self, filepath: os.PathLike | str) -> None:
        if Config.lock_files and _opened_file_nondeletable:
            fpath = pathlib.Path(filepath)
            assert fpath.parent.is_dir()
            self._lockpath = self.make_lock_path(fpath)
        else:
            self._lockpath = pathlib.Path()
        self._lockfile: BinaryIO | None = None

    @staticmethod
    def make_lock_path(filepath: pathlib.Path) -> pathlib.Path:
        f_match = re_media_filename.fullmatch(filepath.name)
        f_id = f_match.group(1)
        f_quality = f'_{Quality(f_match.group(2))}' if f_match.group(2) else ''
        return filepath.with_name(f'{PREFIX}{f_id}{f_quality}.lock')

    async def __aenter__(self) -> FileLock:
        if Config.lock_files and _opened_file_nondeletable:
            try:
                # try to remove existing lock if previous run had its process forcefully terminated
                # raises PermissionError if file exists and is busy
                self._lockpath.unlink(missing_ok=True)
                # open in exclusive mode (create file)
                # raises FileExistsError if file already exists
                self._lockfile = open(self._lockpath, 'bx')
            except OSError:
                raise FileLockError
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if Config.lock_files and _opened_file_nondeletable:
            if self._lockpath.is_file():
                if self._lockfile and not self._lockfile.closed:
                    self._lockfile.close()
                self._lockpath.unlink(missing_ok=True)


def _report_duplicates() -> None:
    found_vs: dict[str, list[str]] = {}
    fvks: list[str] = []
    for k, filenames in _found_filenames_dict.items():
        if not filenames:
            continue
        for fname in filenames:
            if not fname.startswith(PREFIX):
                continue
            fm = re_media_filename.fullmatch(fname)
            if fm:
                fid = fm.group(1)
                if fid not in found_vs:
                    found_vs[fid] = []
                elif fid not in fvks:
                    fvks.append(fid)
                found_vs[fid].append(k + fname)
    if fvks:
        Log.info('Duplicates found:')
        n = '\n  - '
        for kk in fvks:
            Log.info(f' {PREFIX}{kk}.{DEFAULT_EXT}:{n}{n.join(found_vs[kk])}')
    else:
        Log.info('No duplicates found')


def _scan_dest_folder(rescan=False) -> None:
    """
    Scans base destination folder plus {Config.folder_scan_depth} levels of subfolders and
    stores found files in dict (key=folder_name)\n
    |folder1:
    |__subfolder1:
    |____file2
    |____file3
    |__file1
    => files{'folder1': ['file1'], 'subfolder1': ['file2','file3']}\n
    This function may only be called once!
    """
    if rescan:
        _found_filenames_dict.clear()
        _media_matches_cache.clear()

    assert len(_found_filenames_dict.keys()) == 0
    assert len(_media_matches_cache.keys()) == 0
    if os.path.isdir(Config.dest_base) or Config.folder_scan_levelup:
        Log.info('Scanning dest folder...')
        dest_base = Config.dest_base
        scan_depth = Config.folder_scan_depth + Config.folder_scan_levelup
        for _ in range(Config.folder_scan_levelup):
            longpath, dirname = os.path.split(os.path.abspath(dest_base))
            dest_base = normalize_path(longpath)
            if not dirname:
                break

        def _scan_folder(base_folder: str, level: int) -> None:
            if os.path.isdir(base_folder):
                with os.scandir(base_folder) as listing:
                    for dentry in listing:
                        fullpath = f'{base_folder}{dentry.name}'
                        if dentry.is_dir():
                            fullpath = normalize_path(fullpath)
                            if level < scan_depth:
                                _found_filenames_dict[fullpath] = []
                                _scan_folder(fullpath, level + 1)
                        elif dentry.is_file():
                            _found_filenames_dict[base_folder].append(dentry.name)

        _found_filenames_dict[dest_base] = []
        _scan_folder(dest_base, 0)
        if Config.dest_base not in _found_filenames_dict:
            _found_filenames_dict[Config.dest_base] = []
            _scan_folder(Config.dest_base, Config.folder_scan_levelup)
        base_files_count = len(_found_filenames_dict[dest_base])
        total_files_count = sum(len(li) for li in _found_filenames_dict.values())
        Log.info(f'Found {base_files_count:d} file(s) in base and '
                 f'{total_files_count - base_files_count:d} file(s) in {len(_found_filenames_dict.keys()) - 1:d} subfolder(s) '
                 f'(total files: {total_files_count:d}, scan depth: {scan_depth:d})')

    if Config.report_duplicates:
        _report_duplicates()


def _get_media_file_match(fname: str) -> tuple[str, Quality]:
    if fname not in _media_matches_cache:
        f_match = re_media_filename.match(fname)
        f_id, f_quality = (f_match.group(1), Quality(f_match.group(2) or '')) if f_match else ('', '')
        _media_matches_cache[fname] = (f_id, f_quality)
    return _media_matches_cache[fname]


def register_new_file(vi: VideoInfo) -> None:
    base_folder = vi.my_folder
    if not _file_exists_in_folder(base_folder, vi.id, vi.quality, False):
        if _found_filenames_dict.get(base_folder) is None:
            _found_filenames_dict[base_folder] = [vi.filename]
        else:
            _found_filenames_dict[base_folder].append(vi.filename)


def unregister_unfinished_file(vi: VideoInfo) -> None:
    base_folder = vi.my_folder
    if _file_exists_in_folder(base_folder, vi.id, vi.quality, False):
        _found_filenames_dict[base_folder].remove(vi.filename)


def _file_exists_in_folder(base_folder: str, idi: int, quality: Quality, check_folder: bool) -> str:
    orig_file_names = _found_filenames_dict.get(base_folder)
    if orig_file_names is not None and (not check_folder or os.path.isdir(base_folder)):
        for fname in orig_file_names:
            f_id, f_quality = _get_media_file_match(fname)
            if f_id and str(idi) == f_id and (not quality or not f_quality or quality <= f_quality):
                file_full_path = f'{normalize_path(base_folder)}{fname}'
                if check_folder:
                    if not os.path.isfile(file_full_path):
                        Log.warn(f'Warning: _file_exists_in_folder: file \'{file_full_path}\' was found during initial scan '
                                 f'but no longer exists! Re-scanning!')
                        _scan_dest_folder(True)
                        return _file_exists_in_folder(base_folder, idi, quality, False)
                return file_full_path
    return ''


def file_already_exists(idi: int, quality: Quality | None = None, check_folder=True) -> str:
    for fullpath in _found_filenames_dict:
        if filepath := _file_exists_in_folder(fullpath, idi, quality or Config.quality, check_folder):
            return filepath
    return ''


def _file_exists_in_folder_arr(base_folder: str, idi: int, quality: Quality, check_folder: bool) -> list[str]:
    orig_file_names = _found_filenames_dict.get(base_folder)
    folder_files: list[str] = []
    if orig_file_names is not None and (not check_folder or os.path.isdir(base_folder)):
        for fname in orig_file_names:
            f_id, f_quality = _get_media_file_match(fname)
            if f_id and str(idi) == f_id and (not quality or not f_quality or quality == f_quality):
                file_full_path = f'{normalize_path(base_folder)}{fname}'
                if check_folder:
                    if not os.path.isfile(file_full_path):
                        Log.warn(f'Warning: _file_exists_in_folder_arr: file \'{file_full_path}\' was found during initial scan '
                                 f'but no longer exists! Re-scanning!')
                        _scan_dest_folder(True)
                        return _file_exists_in_folder_arr(base_folder, idi, quality, False)
                folder_files.append(file_full_path)
    return folder_files


def file_already_exists_arr(idi: int, quality: Quality | None = None, check_folder=True) -> list[str]:
    found_files: list[str] = []
    for fullpath in _found_filenames_dict:
        found_files.extend(_file_exists_in_folder_arr(fullpath, idi, quality or Config.quality, check_folder))
    return found_files


def prefilter_existing_items(vi_list: MutableSequence[VideoInfo]) -> None:
    """
    This function filters out existing items with desired quality
    (which may sometimes be inaccessible).\n
    This function may only be called once!
    """
    _scan_dest_folder()
    if Config.continue_mode:
        return

    i: int
    for i in reversed(range(len(vi_list))):
        if fullpath := file_already_exists(vi_list[i].id, None, False):
            Log.info(f'Info: {vi_list[i].sname} found in \'{os.path.split(fullpath)[0]}/\'. Skipped.')
            del vi_list[i]


async def try_rename(oldpath: str, newpath: str) -> bool:
    if oldpath == newpath:
        return True

    try:
        newpath_folder = os.path.split(newpath.strip('/'))[0]
        async with FileLock(oldpath):
            os.makedirs(newpath_folder, exist_ok=True)
            os.rename(oldpath, newpath)
        return True
    except Exception:
        return False

#
#
#########################################
