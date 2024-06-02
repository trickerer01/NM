# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import Task, sleep, get_running_loop, as_completed
from os import path, stat, remove, makedirs
from random import uniform as frand
from typing import Optional, List, Dict

from aiofile import async_open
from aiohttp import ClientSession, ClientPayloadError

from config import Config
from defs import (
    Mem, NamingFlags, DownloadResult, CONNECT_RETRIES_BASE, SITE_ITEM_REQUEST_VIDEO, DOWNLOAD_POLICY_ALWAYS, DOWNLOAD_MODE_TOUCH, PREFIX,
    DOWNLOAD_MODE_SKIP, TAGS_CONCAT_CHAR, SITE, SCREENSHOTS_COUNT, QUALITIES, QUALITY_STARTS, QUALITY_ENDS,
    FULLPATH_MAX_BASE_LEN, CONNECT_REQUEST_DELAY,
)
from downloader import VideoDownloadWorker
from dscanner import VideoScanWorker
from dthrottler import ThrottleChecker
from fetch_html import fetch_html, wrap_request, make_session
from logger import Log
from path_util import file_already_exists, try_rename
from rex import re_media_filename, re_private_video
from scenario import DownloadScenario
from tagger import filtered_tags, is_filtered_out_by_extra_tags, unite_separated_tags
from util import has_naming_flag, format_time, get_elapsed_time_i, extract_ext, normalize_path
from vinfo import VideoInfo, export_video_info, get_min_max_ids

__all__ = ('download', 'at_interrupt')


async def download(sequence: List[VideoInfo], by_id: bool, filtered_count: int, session: ClientSession = None) -> None:
    minid, maxid = get_min_max_ids(sequence)
    eta_min = int(2.0 + (CONNECT_REQUEST_DELAY + 0.2 + 0.02) * len(sequence))
    Log.info(f'\nOk! {len(sequence):d} ids (+{filtered_count:d} filtered out), bound {minid:d} to {maxid:d}. Working...\n'
             f'\nThis will take at least {eta_min:d} seconds{f" ({format_time(eta_min)})" if eta_min >= 60 else ""}!\n')
    async with session or make_session() as session:
        if by_id:
            for cv in as_completed([
                VideoScanWorker(sequence, scan_video).run(),
                VideoDownloadWorker(sequence, process_video, filtered_count, session).run()
            ]):
                await cv
        else:
            await VideoDownloadWorker(sequence, download_video, filtered_count, session).run()
    export_video_info(sequence)


async def scan_video(vi: VideoInfo) -> DownloadResult:
    dwn = VideoDownloadWorker.get()
    scn = VideoScanWorker.get()
    scenario = Config.scenario  # type: Optional[DownloadScenario]
    sname = vi.sname
    extra_ids = scn.get_extra_ids() if scn else []  # type: List[int]
    my_tags = 'no_tags'
    rating = vi.rating
    score = ''

    vi.set_state(VideoInfo.State.SCANNING)
    a_html = await fetch_html(SITE_ITEM_REQUEST_VIDEO % vi.id, session=dwn.session)
    if a_html is None:
        Log.error(f'Error: unable to retreive html for {sname}! Aborted!')
        return DownloadResult.FAIL_RETRIES

    if any('Error' in (d.string, d.text) for d in a_html.find_all('legend')):
        error_div = a_html.find('div', class_='text-danger')
        if error_div and 'It is either deleted' in error_div.string:
            Log.error(f'Got error 404 for {sname}, skipping...')
            return DownloadResult.FAIL_NOT_FOUND
        Log.error(f'Warning: Got error 404 for {sname} (probably unlisted), author/score will not be extracted...')
    elif any(re_private_video.search(d.text) for d in a_html.find_all('span', class_='text-danger')):
        Log.warn(f'Warning: Got private video error for {sname}, score(likes)/extra_title will not be extracted...')

    if not vi.title:
        titlemeta = a_html.find('meta', attrs={'name': 'description'})
        vi.title = titlemeta.get('content', '') if titlemeta else ''
    try:
        dislikes_int = int(a_html.find('span', id=f'dislikes_video_{vi.id:d}').text)
        likes_int = int(a_html.find('span', id=f'likes_video_{vi.id:d}').text)
        rating = f'{(likes_int * 100) // (dislikes_int + likes_int):d}' if (dislikes_int + likes_int) > 0 else rating
        score = f'{likes_int - dislikes_int:d}'
    except Exception:
        Log.warn(f'Warning: cannot extract score for {sname}.')
    try:
        try:
            my_author = str(a_html.find('div', class_='card-sub mt-3').find('span', class_='').text).lower()
        except Exception:
            my_author = a_html.find('span', class_='text-danger').find('a').text.lower()
        vi.uploader = my_author
    except Exception:
        Log.warn(f'Warning: cannot extract author for {sname}.')
        my_author = ''
    tdiv = a_html.find('meta', attrs={'name': 'keywords'})
    if tdiv is None:
        Log.info(f'Warning: video {sname} has no tags!')
    tags = unite_separated_tags((str(tdiv.get('content')).replace('\n', ' ') if tdiv else '')
                                .replace(' ', TAGS_CONCAT_CHAR).replace(2 * TAGS_CONCAT_CHAR, TAGS_CONCAT_CHAR).lower())
    tags_raw = [tag.replace(' ', '_') for tag in tags.split(TAGS_CONCAT_CHAR) if len(tag) > 0]
    for add_tag in [ca for ca in [my_author] if len(ca) > 0]:
        if add_tag not in tags_raw:
            tags_raw.append(add_tag)
    if is_filtered_out_by_extra_tags(vi, tags_raw, Config.extra_tags, Config.id_sequence, vi.subfolder, extra_ids):
        Log.info(f'Info: video {sname} is filtered out by{" outer" if scenario is not None else ""} extra tags, skipping...')
        return DownloadResult.FAIL_FILTERED_OUTER if scenario else DownloadResult.FAIL_SKIPPED
    for vsrs, csri, srn, pc in zip((score, rating), (Config.min_score, Config.min_rating), ('score', 'rating'), ('', '%')):
        if len(vsrs) > 0 and csri is not None:
            try:
                if int(vsrs) < csri:
                    Log.info(f'Info: video {sname} has low {srn} \'{vsrs}{pc}\' (required {csri:d}), skipping...')
                    return DownloadResult.FAIL_SKIPPED
            except Exception:
                pass
    if scenario is not None:
        matching_sq = scenario.get_matching_subquery(vi, tags_raw, score, rating)
        utpalways_sq = scenario.get_utp_always_subquery() if tdiv is None else None
        if matching_sq:
            vi.subfolder = matching_sq.subfolder
            vi.quality = matching_sq.quality
        elif utpalways_sq:
            vi.subfolder = utpalways_sq.subfolder
            vi.quality = utpalways_sq.quality
        else:
            Log.info(f'Info: unable to find matching or utp scenario subquery for {sname}, skipping...')
            return DownloadResult.FAIL_SKIPPED
    elif tdiv is None and len(Config.extra_tags) > 0 and Config.utp != DOWNLOAD_POLICY_ALWAYS:
        Log.warn(f'Warning: could not extract tags from {sname}, skipping due to untagged videos download policy...')
        return DownloadResult.FAIL_SKIPPED
    if Config.save_tags:
        vi.tags = ' '.join(tag.replace(' ', '_') for tag in tags_raw)
    if Config.save_descriptions or Config.save_comments:
        cidivs = a_html.find_all('div', class_='comment-body')
        cudivs = [cidiv.find('a', class_='comment-username') for cidiv in cidivs] if cidivs else []
        ctdivs = [cidiv.find('div', class_='comment-text') for cidiv in cidivs] if cidivs else []
        my_uploader = my_author or 'unknown'
        has_description = (cudivs[-1].text.lower() == my_uploader) if cudivs else False  # first comment by uploader
        if Config.save_descriptions:
            desc_comment = (f'{cudivs[-1].text}:\n{ctdivs[-1].text.strip()}') if has_description else ''
            desc_base = ''
            vi.description = desc_base or (f'\n{desc_comment}\n' if desc_comment else '')
        if Config.save_comments:
            comments_list = [f'{cudivs[i].text}:\n{ctdivs[i].text.strip()}' for i in range(len(ctdivs) - int(has_description))]
            vi.comments = ('\n' + '\n\n'.join(comments_list) + '\n') if comments_list else ''
    my_tags = filtered_tags(tags_raw) or my_tags

    prefix = PREFIX if has_naming_flag(NamingFlags.PREFIX) else ''
    fname_part2 = extract_ext(vi.link)
    my_score = (f'{f"+" if score.isnumeric() else ""}{score}' if len(score) > 0
                else '' if len(rating) > 0 else 'unk')
    my_rating = (f'{", " if  len(my_score) > 0 else ""}{rating}{"%" if rating.isnumeric() else ""}' if len(rating) > 0
                 else '' if len(my_score) > 0 else 'unk')
    fname_part1 = (
        f'{prefix}{vi.id:d}'
        f'{f"_({my_score}{my_rating})" if has_naming_flag(NamingFlags.SCORE) else ""}'
        f'{f"_{vi.title}" if vi.title and has_naming_flag(NamingFlags.TITLE) else ""}'
    )
    # <fname_part1>_(<TAGS...>)_<QUALITY><fname_part2>
    extra_len = 2 + 2 + 5  # 2 underscores + 2 brackets + len('1080p') - max len of all qualities
    if has_naming_flag(NamingFlags.TAGS):
        while len(my_tags) > max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part1) + len(fname_part2) + extra_len)):
            my_tags = my_tags[:max(0, my_tags.rfind(TAGS_CONCAT_CHAR))]
        fname_part1 += f'_({my_tags})' if len(my_tags) > 0 else ''
    if len(my_tags) == 0 and len(fname_part1) > max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part2) + extra_len)):
        fname_part1 = fname_part1[:max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part2) + extra_len))]
    fname_part1 = fname_part1.strip()

    vi.filename = fname_part1

    vi.set_state(VideoInfo.State.SCANNED)
    return DownloadResult.SUCCESS


async def process_video(vi: VideoInfo) -> DownloadResult:
    ret_vals = list()
    fname_part1 = vi.filename
    for i in range(QUALITIES.index(vi.quality), len(QUALITIES)):
        vi.link = f'{SITE}/media/videos/{QUALITY_STARTS[i]}{vi.id:d}{QUALITY_ENDS[i]}{extract_ext(vi.link)}'
        fname_mid = f'_{QUALITIES[i]}' if has_naming_flag(NamingFlags.QUALITY) else ''
        vi.filename = f'{fname_part1}{fname_mid}{extract_ext(vi.link)}'
        res = await download_video(vi)
        if res not in (DownloadResult.SUCCESS, DownloadResult.FAIL_SKIPPED, DownloadResult.FAIL_ALREADY_EXISTS):
            ret_vals.append(res)
        else:
            return res
    vi.set_state(VideoInfo.State.FAILED)
    if DownloadResult.FAIL_NOT_FOUND in ret_vals:
        return DownloadResult.FAIL_NOT_FOUND
    else:
        return DownloadResult.FAIL_RETRIES


async def download_sceenshot(vi: VideoInfo, scr_num: int) -> DownloadResult:
    dwn = VideoDownloadWorker.get()
    sname = f'{PREFIX}{vi.id:d}_{scr_num:02d}.jpg'
    sfilename = f'{f"{vi.subfolder}/" if len(vi.subfolder) > 0 else ""}{PREFIX}{vi.id:d}/{scr_num:02d}.jpg'
    my_folder = f'{vi.my_folder}{PREFIX}{vi.id:d}/'
    fullpath = f'{my_folder}{scr_num:02d}.jpg'
    my_link = f'{SITE}/media/videos/tmb2/{vi.id:d}/{scr_num:d}.jpg'
    ret = DownloadResult.SUCCESS

    if not path.isdir(my_folder):
        try:
            makedirs(my_folder)
        except Exception:
            raise IOError(f'ERROR: Unable to create subfolder \'{my_folder}\'!')

    try:
        async with await wrap_request(dwn.session, 'GET', my_link) as r:
            if r.status == 404:
                Log.error(f'Got 404 for {sname}...!')
                ret = DownloadResult.FAIL_NOT_FOUND
            elif r.content_type and 'text' in r.content_type:
                Log.error(f'File not found at {my_link}!')
                ret = DownloadResult.FAIL_NOT_FOUND

            expected_size = r.content_length
            async with async_open(fullpath, 'wb') as outf:
                async for chunk in r.content.iter_chunked(4 * Mem.MB):
                    await outf.write(chunk)

            file_size = stat(fullpath).st_size
            if expected_size and file_size != expected_size:
                Log.error(f'Error: file size mismatch for {sfilename}: {file_size:d} / {expected_size:d}')
                ret = DownloadResult.FAIL_RETRIES
    except Exception:
        ret = DownloadResult.FAIL_NOT_FOUND

    return ret


async def download_sceenshots(vi: VideoInfo) -> DownloadResult:
    ret = DownloadResult.SUCCESS
    for t in [get_running_loop().create_task(download_sceenshot(vi, scr_idx + 1))
              for scr_idx in range(SCREENSHOTS_COUNT)]:  # type: Task[DownloadResult]
        res = await t
        if res not in (DownloadResult.SUCCESS, ret):
            ret = res
    return ret


async def download_video(vi: VideoInfo) -> DownloadResult:
    dwn = VideoDownloadWorker.get()
    retries = 0
    ret = DownloadResult.SUCCESS
    skip = Config.dm == DOWNLOAD_MODE_SKIP
    status_checker = ThrottleChecker(vi)

    if skip is True:
        vi.set_state(VideoInfo.State.DONE)
        ret = DownloadResult.FAIL_SKIPPED
    else:
        vi.set_state(VideoInfo.State.DOWNLOADING)
        curfile_match = re_media_filename.match(vi.filename)
        curfile_quality = curfile_match.group(2)
        curfile = file_already_exists(vi.id, curfile_quality)
        if curfile:
            exact_name = curfile == vi.my_fullpath
            vi.set_flag(VideoInfo.Flags.ALREADY_EXISTED_EXACT if exact_name else VideoInfo.Flags.ALREADY_EXISTED_SIMILAR)
            if Config.continue_mode:
                if not exact_name:
                    curfile_folder, curfile_name = path.split(curfile)
                    same_loc = path.isdir(vi.my_folder) and path.samefile(curfile_folder, vi.my_folder)
                    loc_str = f' ({"same" if same_loc else "different"} location)'
                    if Config.no_rename_move is False or same_loc:
                        Log.info(f'{vi.sffilename} {vi.quality} (or similar) found{loc_str}. Enforcing new name (was \'{curfile}\').')
                        if not try_rename(curfile, vi.my_fullpath):
                            Log.warn(f'Warning: file {vi.sffilename} already exists! Old file will be preserved.')
                    else:
                        new_subfolder = normalize_path(path.relpath(curfile_folder, Config.dest_base))
                        Log.info(f'{vi.sffilename} {vi.quality} (or similar) found{loc_str}. Enforcing old path + new name '
                                 f'\'{curfile_folder}/{vi.filename}\' due to \'--no-rename-move\' flag (was \'{curfile_name}\').')
                        vi.subfolder = new_subfolder
                        if not try_rename(curfile, normalize_path(path.abspath(vi.my_fullpath), False)):
                            Log.warn(f'Warning: file {vi.sffilename} already exists! Old file will be preserved.')
            else:
                Log.info(f'{vi.sffilename} (or similar) already exists. Skipped.\n Location: \'{curfile}\'')
                vi.set_state(VideoInfo.State.DONE)
                return DownloadResult.FAIL_ALREADY_EXISTS
        if not path.isdir(vi.my_folder):
            try:
                makedirs(vi.my_folder)
            except Exception:
                raise IOError(f'ERROR: Unable to create subfolder \'{vi.my_folder}\'!')

    while (not skip) and retries < CONNECT_RETRIES_BASE:
        try:
            file_exists = path.isfile(vi.my_fullpath)
            if file_exists and retries == 0:
                vi.set_flag(VideoInfo.Flags.ALREADY_EXISTED_EXACT)
            file_size = stat(vi.my_fullpath).st_size if file_exists else 0

            if Config.dm == DOWNLOAD_MODE_TOUCH:
                if file_exists:
                    Log.info(f'{vi.sfsname} ({vi.quality}) already exists, size: {file_size:d} ({file_size / Mem.MB:.2f} Mb)')
                    vi.set_state(VideoInfo.State.DONE)
                    return DownloadResult.FAIL_ALREADY_EXISTS
                else:
                    Log.info(f'Saving<touch> {vi.sname} {0.0:.2f} Mb to {vi.sffilename}')
                    with open(vi.my_fullpath, 'wb'):
                        vi.set_flag(VideoInfo.Flags.FILE_WAS_CREATED)
                        vi.set_state(VideoInfo.State.DONE)
                break

            hkwargs = {'headers': {'Range': f'bytes={file_size:d}-'}} if file_size > 0 else {}  # type: Dict[str, Dict[str, str]]
            r = None
            async with await wrap_request(dwn.session, 'GET', vi.link, **hkwargs) as r:
                content_len = r.content_length or 0
                content_range_s = r.headers.get('Content-Range', '/').split('/', 1)
                content_range = int(content_range_s[1]) if len(content_range_s) > 1 and content_range_s[1].isnumeric() else 1
                if (content_len == 0 or r.status == 416) and file_size >= content_range:  # r.status may be 404 also (Apache mishap)
                    Log.warn(f'{vi.sfsname} ({vi.link_quality}) is already completed, size: {file_size:d} ({file_size / Mem.MB:.2f} Mb)')
                    vi.set_state(VideoInfo.State.DONE)
                    ret = DownloadResult.FAIL_ALREADY_EXISTS
                    break
                if r.status == 404:
                    Log.error(f'Got 404 for {vi.sfsname}...!')
                    retries = CONNECT_RETRIES_BASE - 1
                    ret = DownloadResult.FAIL_NOT_FOUND
                if r.content_type and 'text' in r.content_type:
                    Log.error(f'File not found at {vi.link}!')
                    raise FileNotFoundError(vi.link)

                status_checker.prepare(r, file_size)
                vi.expected_size = file_size + content_len
                vi.last_check_size = vi.start_size = file_size
                vi.last_check_time = vi.start_time = get_elapsed_time_i()
                starting_str = f' <continuing at {file_size:d}>' if file_size else ''
                total_str = f' / {vi.expected_size / Mem.MB:.2f}' if file_size else ''
                Log.info(f'Saving{starting_str} {vi.sname} {content_len / Mem.MB:.2f}{total_str} Mb to {vi.sffilename}')

                dwn.add_to_writes(vi)
                vi.set_state(VideoInfo.State.WRITING)
                status_checker.run()
                async with async_open(vi.my_fullpath, 'ab') as outf:
                    vi.set_flag(VideoInfo.Flags.FILE_WAS_CREATED)
                    async for chunk in r.content.iter_chunked(1 * Mem.MB):
                        await outf.write(chunk)
                status_checker.reset()
                dwn.remove_from_writes(vi)

                file_size = stat(vi.my_fullpath).st_size
                if vi.expected_size and file_size != vi.expected_size:
                    Log.error(f'Error: file size mismatch for {vi.sfsname}: {file_size:d} / {vi.expected_size:d}')
                    raise IOError(vi.link)

                vi.set_state(VideoInfo.State.DONE)
                break
        except Exception as e:
            import sys
            print(sys.exc_info()[0], sys.exc_info()[1])
            if (r is None or r.status != 403) and isinstance(e, ClientPayloadError) is False:
                retries += 1
                Log.error(f'{vi.sffilename}: error #{retries:d}...')
            if r is not None and r.closed is False:
                r.close()
            # Network error may be thrown before item is added to active downloads
            if dwn.is_writing(vi):
                dwn.remove_from_writes(vi)
            status_checker.reset()
            if retries < CONNECT_RETRIES_BASE:
                vi.set_state(VideoInfo.State.DOWNLOADING)
                await sleep(frand(1.0, 7.0))
            elif Config.keep_unfinished is False and path.isfile(vi.my_fullpath) and vi.has_flag(VideoInfo.Flags.FILE_WAS_CREATED):
                Log.error(f'Failed to download {vi.sffilename}. Removing unfinished file...')
                remove(vi.my_fullpath)

    ret = (ret if ret in (DownloadResult.FAIL_NOT_FOUND, DownloadResult.FAIL_SKIPPED, DownloadResult.FAIL_ALREADY_EXISTS) else
           DownloadResult.SUCCESS if retries < CONNECT_RETRIES_BASE else
           DownloadResult.FAIL_RETRIES)

    if Config.save_screenshots:
        sret = await download_sceenshots(vi)
        if sret != DownloadResult.SUCCESS:
            Log.warn(f'{vi.sffilename}: `download_sceenshots()` has failed items (ret = {str(sret)})')

    return ret


def at_interrupt() -> None:
    dwn = VideoDownloadWorker.get()
    if dwn is not None:
        return dwn.at_interrupt()

#
#
#########################################
