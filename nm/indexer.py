# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import contextlib
import functools
import json
import os
import pathlib
import time
from asyncio import sleep
from collections import defaultdict
from collections.abc import Iterable, MutableSequence
from typing import TextIO, TypedDict

from .config import Config
from .defs import DEFAULT_EXT, FOLDER_INDEX_FILENAME, FOLDER_INDEX_INDENT, PREFIX, QUALITIES, UTF8, NamingFlags, Quality
from .iinfo import VideoInfo
from .logger import Log
from .path_util import FileLock, FileLockError
from .rex import re_media_filename
from .util import calc_sleep_time_retry, has_naming_flag, normalize_path

__all__ = (
    'FolderIndexer',
    'file_already_exists',
    'file_already_exists_arr',
    'prefilter_existing_items',
    'register_finished_file',
    'register_new_file',
    'unregister_unfinished_file',
)

# LEGACY
_found_filenames_dict: dict[str, list[str]] = {}
_media_matches_cache: dict[str, tuple[str, Quality]] = {}


def _report_duplicates_legacy() -> None:
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


def _scan_dest_folder_legacy(rescan=False) -> None:
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

        def _scan_folder_legacy(base_folder: str, level: int) -> None:
            if os.path.isdir(base_folder):
                with os.scandir(base_folder) as listing:
                    for dentry in listing:
                        fullpath = f'{base_folder}{dentry.name}'
                        if dentry.is_dir():
                            fullpath = normalize_path(fullpath)
                            if level < scan_depth:
                                _found_filenames_dict[fullpath] = []
                                _scan_folder_legacy(fullpath, level + 1)
                        elif dentry.is_file():
                            _found_filenames_dict[base_folder].append(dentry.name)

        _found_filenames_dict[dest_base] = []
        _scan_folder_legacy(dest_base, 0)
        if Config.dest_base not in _found_filenames_dict:
            _found_filenames_dict[Config.dest_base] = []
            _scan_folder_legacy(Config.dest_base, Config.folder_scan_levelup)
        base_files_count = len(_found_filenames_dict[dest_base])
        total_files_count = sum(len(li) for li in _found_filenames_dict.values())
        Log.info(f'Found {base_files_count:d} file(s) in base and '
                 f'{total_files_count - base_files_count:d} file(s) in {len(_found_filenames_dict.keys()) - 1:d} subfolder(s) '
                 f'(total files: {total_files_count:d}, scan depth: {scan_depth:d})')

    if Config.report_duplicates:
        _report_duplicates_legacy()


def _get_media_file_match_legacy(fname: str) -> tuple[str, Quality]:
    if fname not in _media_matches_cache:
        f_match = re_media_filename.match(fname)
        f_id, f_quality = (f_match.group(1), Quality(f_match.group(2) or '')) if f_match else ('', '')
        _media_matches_cache[fname] = (f_id, f_quality)
    return _media_matches_cache[fname]


def _register_new_file_legacy(vi: VideoInfo) -> None:
    base_folder = vi.my_folder
    if not _file_exists_in_folder_legacy(base_folder, vi.id, vi.quality, False):
        if _found_filenames_dict.get(base_folder) is None:
            _found_filenames_dict[base_folder] = [vi.filename]
        else:
            _found_filenames_dict[base_folder].append(vi.filename)


def _unregister_unfinished_file_legacy(vi: VideoInfo) -> None:
    base_folder = vi.my_folder
    if _file_exists_in_folder_legacy(base_folder, vi.id, vi.quality, False):
        _found_filenames_dict[base_folder].remove(vi.filename)


def _file_exists_in_folder_legacy(base_folder: str, idi: int, quality: Quality, check_folder: bool) -> str:
    orig_file_names = _found_filenames_dict.get(base_folder)
    if orig_file_names is not None and (not check_folder or os.path.isdir(base_folder)):
        for fname in orig_file_names:
            f_id, f_quality = _get_media_file_match_legacy(fname)
            if f_id and str(idi) == f_id and (not quality or not f_quality or quality <= f_quality):
                file_full_path = f'{normalize_path(base_folder)}{fname}'
                if check_folder:
                    if not os.path.isfile(file_full_path):
                        Log.warn(f'Warning: _file_exists_in_folder_legacy: file \'{file_full_path}\' was found during initial scan '
                                 f'but no longer exists! Re-scanning!')
                        _scan_dest_folder_legacy(True)
                        return _file_exists_in_folder_legacy(base_folder, idi, quality, False)
                return file_full_path
    return ''


def _file_already_exists_legacy(idi: int, quality: Quality | None = None, check_folder=True) -> str:
    for fullpath in _found_filenames_dict:
        if filepath := _file_exists_in_folder_legacy(fullpath, idi, quality or Config.quality, check_folder):
            return filepath
    return ''


def _file_exists_in_folder_arr_legacy(base_folder: str, idi: int, quality: Quality, check_folder: bool) -> list[str]:
    orig_file_names = _found_filenames_dict.get(base_folder)
    folder_files: list[str] = []
    if orig_file_names is not None and (not check_folder or os.path.isdir(base_folder)):
        for fname in orig_file_names:
            f_id, f_quality = _get_media_file_match_legacy(fname)
            if f_id and str(idi) == f_id and (not quality or not f_quality or quality == f_quality):
                file_full_path = f'{normalize_path(base_folder)}{fname}'
                if check_folder:
                    if not os.path.isfile(file_full_path):
                        Log.warn(f'Warning: _file_exists_in_folder_arr_legacy: file \'{file_full_path}\' was found during initial scan '
                                 f'but no longer exists! Re-scanning!')
                        _scan_dest_folder_legacy(True)
                        return _file_exists_in_folder_arr_legacy(base_folder, idi, quality, False)
                folder_files.append(file_full_path)
    return folder_files


def _file_already_exists_arr_legacy(idi: int, quality: Quality | None = None, check_folder=True) -> list[str]:
    found_files: list[str] = []
    for fullpath in _found_filenames_dict:
        found_files.extend(_file_exists_in_folder_arr_legacy(fullpath, idi, quality or Config.quality, check_folder))
    return found_files


def _prefilter_existing_items_legacy(vi_list: MutableSequence[VideoInfo]) -> None:
    """
    This function filters out existing items with desired quality
    (which may sometimes be inaccessible).\n
    This function may only be called once!
    """
    if Config.continue_mode:
        return

    i: int
    for i in reversed(range(len(vi_list))):
        if fullpath := _file_already_exists_legacy(vi_list[i].id, None, False):
            Log.info(f'Info: {vi_list[i].sname} found in \'{os.path.split(fullpath)[0]}/\'. Skipped.')
            del vi_list[i]


def register_new_file(vi: VideoInfo) -> None:
    return _register_new_file_legacy(vi)


def unregister_unfinished_file(vi: VideoInfo) -> None:
    return _unregister_unfinished_file_legacy(vi)


# END LEGACY

_indexed_folders: dict[pathlib.Path, list[pathlib.Path]] = {}


class FolderIndex(TypedDict):
    pids: list[str]
    files: list[tuple[str, str]]


class FolderIndexer:
    def __init__(self) -> None:
        pass

    async def __aenter__(self) -> FolderIndexer:
        if Config.lock_files:
            await _scan_dest_folder()
        else:
            _scan_dest_folder_legacy()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if Config.lock_files:
            await _clean_indexer()


def _folder_index_default() -> FolderIndex:
    return FolderIndex(pids=[], files=[])


def _try_read_index_file(indexfile: TextIO) -> FolderIndex:
    try:
        return json.load(indexfile)
    except json.JSONDecodeError:
        return _folder_index_default()


def _report_duplicates(files: dict[str, list[pathlib.Path]]) -> None:
    found_dupes: dict[str, list[str]] = {}
    for fid, filepaths in files.items():
        if len(filepaths) < 2:
            continue
        found_dupes[fid] = [_.as_posix() for _ in filepaths]
    if found_dupes:
        Log.info('Duplicates found:')
        n = '\n  - '
        Log.info('\n'.join(f' {PREFIX}{_}.{DEFAULT_EXT}:{n}{n.join(found_dupes[_])}' for _ in found_dupes))
    else:
        Log.info('No duplicates found')


@functools.lru_cache(maxsize=256)
def _get_media_file_match(filename: str | pathlib.Path) -> tuple[str, Quality]:
    fname = filename.name if isinstance(filename, pathlib.Path) else str(filename)
    f_match = re_media_filename.match(fname)
    f_id, f_quality = (f_match.group(1), Quality(f_match.group(2) or '')) if f_match else ('', '')
    return f_id, f_quality


def _to_index_name(id_: str, quality: str) -> str:
    return f'{PREFIX}{id_}{f"_{quality}" if quality else ""}'


def _from_index_name(index_name: str) -> tuple[str, str]:
    sname = index_name[len(PREFIX):]
    if '_' in sname:
        id_, quality = tuple(sname.split('_', 1))
        return id_, quality
    return sname, ''


def _index_filename(filename: str) -> str:
    id_, quality = _get_media_file_match(filename)
    if id_:
        return _to_index_name(id_, quality)
    return ''


def _get_file_path_from_index(index_json: FolderIndex, id_: str | int, quality: Quality) -> pathlib.Path | None:
    if 'files' in index_json:
        bname = _to_index_name(str(id_), '')
        qname = _to_index_name(str(id_), quality) if quality else bname
        if qname != bname:
            for ftup in index_json['files']:
                if ftup[0] == qname:
                    return pathlib.Path(ftup[1])
            return None
        if bnames := [fpath for fname, fpath in index_json['files'] if fname.startswith(bname)]:
            return pathlib.Path(bnames[-1])
    return None


async def _scan_dest_folder(rescan=False) -> None:
    if rescan:
        _get_media_file_match.cache_clear()
        _indexed_folders.clear()

    assert _get_media_file_match.cache_info().currsize == 0
    assert len(_indexed_folders) == 0

    found_files: dict[str, list[pathlib.Path]] = defaultdict(list)

    dest_base = Config.dest_base
    if os.path.isdir(Config.dest_base) or Config.folder_scan_levelup:
        Log.info('Scanning dest folder...')
        scan_depth = Config.folder_scan_depth + Config.folder_scan_levelup
        for _ in range(Config.folder_scan_levelup):
            longpath, dirname = os.path.split(os.path.abspath(dest_base))
            dest_base = normalize_path(longpath)
            if not dirname:
                break

        dest_base_path = pathlib.Path(dest_base)
        dest_base_cpath = pathlib.Path(Config.dest_base)

        def _scan_folder(base_folder: pathlib.Path, level: int) -> None:
            with os.scandir(base_folder.as_posix()) as listing:
                for dentry in listing:
                    fullpath = base_folder / dentry.name
                    if dentry.is_dir():
                        if level < scan_depth:
                            _indexed_folders[fullpath] = []
                            _scan_folder(fullpath, level + 1)
                    elif dentry.is_file():
                        if fm := re_media_filename.match(fullpath.name):
                            if has_naming_flag(NamingFlags.PREFIX) and not fullpath.name.startswith(PREFIX):
                                continue
                            _indexed_folders[base_folder].append(fullpath)
                            found_files[fm.group(1)].append(fullpath)

        if dest_base_path.is_dir():
            _indexed_folders[dest_base_path] = []
            _scan_folder(dest_base_path, 0)
        if dest_base_cpath not in _indexed_folders and dest_base_cpath.is_dir():
            _indexed_folders[dest_base_cpath] = []
            _scan_folder(dest_base_cpath, Config.folder_scan_levelup)

        base_files_count = len(_indexed_folders[dest_base_path])
        total_files_count = sum(len(li) for li in _indexed_folders.values())
        Log.info(f'Found {base_files_count:d} file(s) in base and '
                 f'{total_files_count - base_files_count:d} file(s) in {max(len(_indexed_folders) - 1, 0):d} subfolder(s) '
                 f'(total files: {total_files_count:d}, scan depth: {scan_depth:d})')

    if _indexed_folders:
        pid = str(os.getpid())
        while True:
            async with contextlib.AsyncExitStack() as flocks:
                try:
                    [await flocks.enter_async_context(FileLock(_ / FOLDER_INDEX_FILENAME)) for _ in _indexed_folders]
                except FileLockError:
                    Log.warn(f'Warning: _scan_dest_folder: Unable to acquire a lock on {dest_base} and its subfolders! Waiting...')
                    await sleep(calc_sleep_time_retry(None) * 2)
                    continue
                open_mode = 'wt+' if Config.master_instance else 'at+'
                for fdirpath, fdirfiles in _indexed_folders.items():
                    with open(fdirpath / FOLDER_INDEX_FILENAME, open_mode, encoding=UTF8, errors='replace') as indexfile:
                        indexfile.seek(0)
                        fdir_index_json = _try_read_index_file(indexfile)
                        fdir_index_json['pids'] = (fdir_index_json.get('pids') or []) + [pid]
                        fdir_index_json['files'] = [(pname, _.as_posix()) for _ in fdirfiles if (pname := _index_filename(_.name))]
                        indexfile.flush()
                        indexfile.seek(0)
                        indexfile.truncate()
                        json.dump(fdir_index_json, indexfile, indent=FOLDER_INDEX_INDENT)
                        indexfile.write('\n')
            break

    if Config.report_duplicates:
        _report_duplicates(found_files)


async def _clean_indexer() -> None:
    dirpaths = [_ for _ in _indexed_folders if _.is_dir()]
    if not dirpaths:
        return
    Log.trace('\nPerforming index cleanup...')
    pid = str(os.getpid())
    while True:
        async with contextlib.AsyncExitStack() as flocks:
            try:
                [await flocks.enter_async_context(FileLock(_ / FOLDER_INDEX_FILENAME)) for _ in dirpaths]
            except FileLockError:
                Log.warn(f'Warning: _clean_indexer: Unable to acquire a lock on {Config.dest_base} and its subfolders! Waiting...')
                await sleep(calc_sleep_time_retry(None) * 2)
                continue
            for fdirpath in dirpaths:
                indexpath = fdirpath / FOLDER_INDEX_FILENAME
                with open(indexpath, 'at+', encoding=UTF8, errors='replace') as indexfile:
                    indexfile.seek(0)
                    fdir_index_json = _try_read_index_file(indexfile)
                    fdir_index_json['pids'] = (fdir_index_json.get('pids') or [])
                    if pid in fdir_index_json['pids']:
                        fdir_index_json['pids'].remove(pid)
                    last_pid = not fdir_index_json['pids']
                    if not last_pid:
                        indexfile.flush()
                        indexfile.seek(0)
                        indexfile.truncate()
                        json.dump(fdir_index_json, indexfile, indent=FOLDER_INDEX_INDENT)
                        indexfile.write('\n')
                if last_pid:
                    indexpath.unlink(missing_ok=True)
        break
    Log.trace('Done')


async def register_finished_file(vi: VideoInfo) -> None:
    if Config.lock_files is False:
        return

    Log.trace(f'Adding {vi.sfsname} to index...')
    base_folder = pathlib.Path(vi.my_folder)
    folder_index_file_path = base_folder / FOLDER_INDEX_FILENAME
    if not folder_index_file_path.is_file():
        Log.warn(f'Warning: register_finished_file: index file \'{FOLDER_INDEX_FILENAME}\' was NOT found in {base_folder.as_posix()}! '
                 f'Re-scanning!')
        return await _scan_dest_folder(True)

    while True:
        try:
            async with FileLock(folder_index_file_path):
                with open(folder_index_file_path, 'at+', encoding=UTF8, errors='replace') as indexfile:
                    indexfile.seek(0)
                    index_json = _try_read_index_file(indexfile)
                    index_json['files'] = index_json['files'] or []
                    index_json['files'].append((_index_filename(vi.filename), vi.my_fullpath))
                    indexfile.flush()
                    indexfile.seek(0)
                    indexfile.truncate()
                    json.dump(index_json, indexfile, indent=FOLDER_INDEX_INDENT)
                    indexfile.write('\n')
        except FileLockError:
            Log.warn(f'Warning: register_finished_file: Unable to acquire a lock on {folder_index_file_path}! Waiting...')
            await sleep(calc_sleep_time_retry(None) * 2)
            continue
        break


def timed_cache(max_age_seconds: int, max_size=1024, typed=False):
    def _decorator(func):
        @functools.lru_cache(maxsize=max_size, typed=typed)
        def _new(*args, _expire: int, **kwargs):
            return func(*args, **kwargs)

        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            return _new(*args, _expire=int(time.time() // max_age_seconds), **kwargs)
        return _wrapped
    return _decorator


@timed_cache(10)
def _read_index_json_cached(folder_index_file_path: pathlib.Path) -> FolderIndex:
    with open(folder_index_file_path, 'at+', encoding=UTF8) as indexfile:
        indexfile.seek(0)
        index_json = _try_read_index_file(indexfile)
        return index_json


async def _file_exists_in_folder(base_folder: pathlib.Path, idi: int, qualities: Iterable[Quality]) -> list[pathlib.Path]:
    folder_index_file_path = base_folder / FOLDER_INDEX_FILENAME
    if not folder_index_file_path.is_file():
        if not folder_index_file_path.parent.is_dir():
            return []
        Log.warn(f'Warning: _file_exists_in_folder: index file \'{FOLDER_INDEX_FILENAME}\' was NOT found in {base_folder.as_posix()}! '
                 f'Re-scanning!')
        await _scan_dest_folder(True)
        return await _file_exists_in_folder(base_folder, idi, qualities)

    while True:
        try:
            index_json = _read_index_json_cached(folder_index_file_path)
            break
        except Exception:
            Log.warn(f'Warning: _file_exists_in_folder: Unable to acquire a lock on {folder_index_file_path}! Waiting...')
            await sleep(calc_sleep_time_retry(None) * 2)

    fpaths: list[pathlib.Path] = []
    if index_json['files']:
        for q in qualities:
            if fpath := _get_file_path_from_index(index_json, idi, q or ''):
                fpaths.append(fpath)
    return fpaths


async def file_already_exists(idi: int, quality: Quality | None = None, check_folder=True) -> pathlib.Path | None:
    if Config.lock_files is False:
        return pathlib.Path(lres) if (lres := _file_already_exists_legacy(idi, quality, check_folder)) else None
    # container may change during iteration
    for folder_path in list(_indexed_folders.keys()):
        if filepaths := await _file_exists_in_folder(folder_path, idi, (quality or Config.quality,)):
            return filepaths[-1]
    return None


async def _file_exists_in_folder_arr(base_folder: pathlib.Path, idi: int, quality: Quality) -> list[pathlib.Path]:
    return await _file_exists_in_folder(base_folder, idi, [quality] if quality else QUALITIES)


async def file_already_exists_arr(idi: int, quality: Quality | None = None, check_folder=True) -> list[str]:
    if Config.lock_files is False:
        return _file_already_exists_arr_legacy(idi, quality, check_folder)
    found_files: list[str] = []
    # container may change during iteration
    for folder_path in list(_indexed_folders.keys()):
        found_files.extend([_.as_posix() for _ in await _file_exists_in_folder_arr(folder_path, idi, quality or Config.quality)])
    return found_files


async def prefilter_existing_items(vi_list: MutableSequence[VideoInfo]) -> None:
    """
    This function filters out existing items with desired quality
    (which may sometimes be inaccessible).\n
    This function may only be called once!
    """
    if Config.lock_files is False:
        return _prefilter_existing_items_legacy(vi_list)

    if Config.continue_mode:
        return

    i: int
    for i in reversed(range(len(vi_list))):
        if fullpath := await file_already_exists(vi_list[i].id, None):
            Log.info(f'Info: {vi_list[i].sname} found in \'{fullpath.parent.as_posix()}/\'. Skipped.')
            del vi_list[i]

#
#
#########################################
