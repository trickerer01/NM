# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from os import path, listdir, rename, makedirs
from typing import List, Dict, MutableSequence

from config import Config
from defs import Quality, PREFIX, DEFAULT_EXT
from logger import Log
from rex import re_media_filename
from util import normalize_path
from vinfo import VideoInfo

__all__ = ('file_already_exists', 'file_already_exists_arr', 'try_rename', 'prefilter_existing_items')

found_filenames_dict: Dict[str, List[str]] = dict()


def report_duplicates() -> None:
    found_vs = dict()
    fvks = list()
    for k in found_filenames_dict:
        if not found_filenames_dict[k]:
            continue
        for fname in found_filenames_dict[k]:
            if not fname.startswith(PREFIX):
                continue
            fm = re_media_filename.fullmatch(fname)
            if fm:
                fid = fm.group(1)
                if fid not in found_vs:
                    found_vs[fid] = [''] * 0
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


def scan_dest_folder() -> None:
    """
    Scans base destination folder plus {Config.folder_scan_depth} levels of subfolders and
    stores found files in dict (key=folder_name)\n\n
    |folder1:\n\n
    |__subfolder1:\n\n
    |____file2\n\n
    |____file3\n\n
    |__file1\n\n
    => files{'folder1': ['file1'], 'subfolder1': ['file2','file3']}\n\n
    This function may only be called once!
    """
    assert len(found_filenames_dict.keys()) == 0
    if path.isdir(Config.dest_base) or Config.folder_scan_levelup:
        Log.info('Scanning dest folder...')
        dest_base = Config.dest_base
        scan_depth = Config.folder_scan_depth + Config.folder_scan_levelup
        for _ in range(Config.folder_scan_levelup):
            longpath, dirname = path.split(path.abspath(dest_base))
            dest_base = normalize_path(longpath)
            if dirname == '':
                break

        def scan_folder(base_folder: str, level: int) -> None:
            if path.isdir(base_folder):
                for cname in listdir(base_folder):
                    fullpath = f'{base_folder}{cname}'
                    if path.isdir(fullpath):
                        fullpath = normalize_path(fullpath)
                        if level < scan_depth:
                            found_filenames_dict[fullpath] = list()
                            scan_folder(fullpath, level + 1)
                    elif path.isfile(fullpath):
                        found_filenames_dict[base_folder].append(cname)

        found_filenames_dict[dest_base] = list()
        scan_folder(dest_base, 0)
        if Config.dest_base not in found_filenames_dict:
            found_filenames_dict[Config.dest_base] = list()
            scan_folder(Config.dest_base, Config.folder_scan_levelup)
        base_files_count = len(found_filenames_dict[dest_base])
        total_files_count = sum(len(li) for li in found_filenames_dict.values())
        Log.info(f'Found {base_files_count:d} file(s) in base and '
                 f'{total_files_count - base_files_count:d} file(s) in {len(found_filenames_dict.keys()) - 1:d} subfolder(s) '
                 f'(total files: {total_files_count:d}, scan depth: {scan_depth:d})')

    if Config.report_duplicates:
        report_duplicates()


def file_exists_in_folder(base_folder: str, idi: int, quality: Quality) -> str:
    orig_file_names = found_filenames_dict.get(normalize_path(base_folder))
    if path.isdir(base_folder) and orig_file_names is not None:
        for fname in orig_file_names:
            try:
                f_match = re_media_filename.match(fname)
                f_id = f_match.group(1)
                f_quality = Quality(f_match.group(2) or '')
                if str(idi) == f_id and (not quality or not f_quality or quality <= f_quality):
                    return f'{normalize_path(base_folder)}{fname}'
            except Exception:
                continue
    return ''


def file_already_exists(idi: int, quality: Quality) -> str:
    for fullpath in found_filenames_dict:
        fullpath = file_exists_in_folder(fullpath, idi, quality or Config.quality)
        if len(fullpath) > 0:
            return fullpath
    return ''


def file_exists_in_folder_arr(base_folder: str, idi: int, quality: Quality) -> List[str]:
    orig_file_names = found_filenames_dict.get(normalize_path(base_folder))
    folder_files = list()
    if path.isdir(base_folder) and orig_file_names is not None:
        for fname in orig_file_names:
            try:
                f_match = re_media_filename.match(fname)
                f_id = f_match.group(1)
                f_quality = Quality(f_match.group(2) or '')
                if str(idi) == f_id and (not quality or not f_quality or quality == f_quality):
                    folder_files.append(f'{normalize_path(base_folder)}{fname}')
            except Exception:
                continue
    return folder_files


def file_already_exists_arr(idi: int, quality: Quality) -> List[str]:
    found_files = list()
    for fullpath in found_filenames_dict:
        found_files.extend(file_exists_in_folder_arr(fullpath, idi, quality or Config.quality))
    return found_files


def prefilter_existing_items(vi_list: MutableSequence[VideoInfo]) -> None:
    """
    This function filters out existing items with desired quality\n\n
    (which may sometimes be inaccessible).\n\n
    This function may only be called once!
    """
    scan_dest_folder()
    if Config.continue_mode:
        return

    i: int
    for i in reversed(range(len(vi_list))):
        fullpath = file_already_exists(vi_list[i].id, Quality())
        if len(fullpath) > 0:
            Log.info(f'Info: {vi_list[i].sname} found in \'{path.split(fullpath)[0]}/\'. Skipped.')
            del vi_list[i]


def try_rename(oldpath: str, newpath: str) -> bool:
    try:
        if oldpath == newpath:
            return True
        newpath_folder = path.split(newpath.strip('/'))[0]
        if not path.isdir(newpath_folder):
            makedirs(newpath_folder)
        rename(oldpath, newpath)
        return True
    except Exception:
        return False

#
#
#########################################
