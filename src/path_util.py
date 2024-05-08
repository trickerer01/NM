# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from os import path, listdir, rename
from typing import List, Optional, Dict, MutableSequence

from config import Config
from defs import MAX_DEST_SCAN_SUB_DEPTH
from logger import Log
from rex import re_media_filename
from scenario import DownloadScenario
from util import normalize_path
from vinfo import VideoInfo

__all__ = ('file_already_exists', 'try_rename', 'prefilter_existing_items')

found_filenames_dict = dict()  # type: Dict[str, List[str]]


def scan_dest_folder() -> None:
    """
    Scans base destination folder plus {MAX_DEST_SCAN_SUB_DEPTH} levels of subfolders and
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
    if path.isdir(Config.dest_base):
        Log.info('Scanning dest folder...')

        def scan_folder(base_folder: str, level: int) -> None:
            for cname in listdir(base_folder):
                fullpath = f'{base_folder}{cname}'
                if path.isdir(fullpath):
                    fullpath = normalize_path(fullpath)
                    if level < MAX_DEST_SCAN_SUB_DEPTH:
                        found_filenames_dict[fullpath] = list()
                        scan_folder(fullpath, level + 1)
                elif path.isfile(fullpath):
                    found_filenames_dict[base_folder].append(cname)

        found_filenames_dict[Config.dest_base] = list()
        scan_folder(Config.dest_base, 0)
        base_files_count = len(found_filenames_dict.get(Config.dest_base))
        total_files_count = sum(len(li) for li in found_filenames_dict.values())
        Log.info(f'Found {base_files_count:d} file(s) in base and '
                 f'{total_files_count - base_files_count:d} file(s) in {len(found_filenames_dict.keys()) - 1:d} subfolder(s) '
                 f'(total files: {total_files_count:d}, scan depth: {MAX_DEST_SCAN_SUB_DEPTH:d})')


def file_exists_in_folder(base_folder: str, idi: int, quality: str) -> str:
    orig_file_names = found_filenames_dict.get(normalize_path(base_folder))
    if path.isdir(base_folder) and orig_file_names is not None:
        for fname in orig_file_names:
            try:
                f_match = re_media_filename.match(fname)
                f_id = f_match.group(1)
                f_quality = f_match.group(2)
                if str(idi) == f_id and (quality is None or quality == f_quality):
                    return f'{normalize_path(base_folder)}{fname}'
            except Exception:
                continue
    return ''


def file_already_exists(idi: int, quality: str) -> str:
    scenario = Config.scenario  # type: Optional[DownloadScenario]
    if scenario:
        for q in scenario.queries:
            fullpath = file_exists_in_folder(f'{Config.dest_base}{q.subfolder}', idi, quality or q.quality)
            if len(fullpath) > 0:
                return fullpath
    else:
        for fullpath in found_filenames_dict:
            fullpath = file_exists_in_folder(fullpath, idi, quality or Config.quality)
            if len(fullpath) > 0:
                return fullpath
    return ''


def prefilter_existing_items(vi_list: MutableSequence[VideoInfo]) -> None:
    """
    This function filters out existing items with desired quality\n\n
    (which may sometimes be inaccessible).\n\n
    This function may only be called once!
    """
    scan_dest_folder()
    if Config.continue_mode:
        return

    for i in reversed(range(len(vi_list))):  # type: int
        fullpath = file_already_exists(vi_list[i].id, '')
        if len(fullpath) > 0:
            Log.info(f'Info: {vi_list[i].sname} found in \'{path.split(fullpath)[0]}/\'. Skipped.')
            del vi_list[i]


def try_rename(oldpath: str, newpath: str) -> bool:
    try:
        rename(oldpath, newpath)
        return True
    except Exception:
        return False

#
#
#########################################
