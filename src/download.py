# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import Task, CancelledError, sleep, get_running_loop
from os import path, stat, remove, makedirs, rename
from random import uniform as frand
from typing import Optional, List, Dict

from aiofile import async_open
from aiohttp import ClientSession, ClientResponse, ClientPayloadError

from config import Config
from defs import (
    Mem, NamingFlags, DownloadResult, CONNECT_RETRIES_BASE, SITE_ITEM_REQUEST_VIDEO, DOWNLOAD_POLICY_ALWAYS, DOWNLOAD_MODE_TOUCH, PREFIX,
    DOWNLOAD_MODE_SKIP, TAGS_CONCAT_CHAR, DOWNLOAD_STATUS_CHECK_TIMER, SITE, SCREENSHOTS_COUNT, QUALITIES, QUALITY_STARTS, QUALITY_ENDS,
    FULLPATH_MAX_BASE_LEN,
)
from downloader import VideoDownloadWorker
from fetch_html import fetch_html, wrap_request, make_session
from logger import Log
from path_util import file_already_exists
from rex import re_media_filename, re_private_video
from scenario import DownloadScenario
from tagger import filtered_tags, is_filtered_out_by_extra_tags, unite_separated_tags
from util import has_naming_flag, get_elapsed_time_i, extract_ext
from vinfo import VideoInfo, export_video_info, get_min_max_ids

__all__ = ('download', 'at_interrupt')


async def download(sequence: List[VideoInfo], by_id: bool, filtered_count: int, session: ClientSession = None) -> None:
    minid, maxid = get_min_max_ids(sequence)
    Log.info(f'\nOk! {len(sequence):d} ids (+{filtered_count:d} filtered out), bound {minid:d} to {maxid:d}. Working...\n')
    async with session or make_session() as session:
        await VideoDownloadWorker(sequence, (download_video, process_video)[by_id], filtered_count, session).run()
    export_video_info(sequence)


async def process_video(vi: VideoInfo) -> DownloadResult:
    dwn = VideoDownloadWorker.get()
    scenario = Config.scenario  # type: Optional[DownloadScenario]
    sname = vi.sname
    my_tags = 'no_tags'
    rating = vi.my_rating
    score = ''

    vi.set_state(VideoInfo.State.ACTIVE)
    a_html = await fetch_html(SITE_ITEM_REQUEST_VIDEO % vi.my_id, session=dwn.session)
    if a_html is None:
        Log.error(f'Error: unable to retreive html for {sname}! Aborted!')
        return DownloadResult.FAIL_RETRIES

    if any('Error' in (d.string, d.text) for d in a_html.find_all('legend')):
        Log.error(f'Warning: Got error 404 for {sname} (probably unlisted), author/score will not be extracted...')
    elif any(re_private_video.search(d.text) for d in a_html.find_all('span', class_='text-danger')):
        Log.warn(f'Warning: Got private video error for {sname}, score(likes)/extra_title will not be extracted...')

    if not vi.my_title:
        titlemeta = a_html.find('meta', attrs={'name': 'description'})
        vi.my_title = titlemeta.get('content', '') if titlemeta else ''
    try:
        dislikes_int = int(a_html.find('span', id=f'dislikes_video_{vi.my_id:d}').text)
        likes_int = int(a_html.find('span', id=f'likes_video_{vi.my_id:d}').text)
        rating = f'{(likes_int * 100) // (dislikes_int + likes_int):d}' if (dislikes_int + likes_int) > 0 else rating
        score = f'{likes_int - dislikes_int:d}'
    except Exception:
        Log.warn(f'Warning: cannot extract score for {sname}.')
    try:
        try:
            my_author = str(a_html.find('div', class_='card-sub mt-3').find('span', class_='').text).lower()
        except Exception:
            my_author = a_html.find('span', class_='text-danger').find('a').text.lower()
    except Exception:
        Log.warn(f'Warning: cannot extract author for {sname}.')
        my_author = ''
    tdiv = a_html.find('meta', attrs={'name': 'keywords'})
    if tdiv is None:
        Log.info(f'Warning: video {sname} has no tags!')
    tags = unite_separated_tags((str(tdiv.get('content')) if tdiv else '').replace(' ', TAGS_CONCAT_CHAR).lower())
    tags_raw = [tag.replace(' ', '_') for tag in tags.split(TAGS_CONCAT_CHAR) if len(tag) > 0]
    for add_tag in [ca for ca in [my_author] if len(ca) > 0]:
        if add_tag not in tags_raw:
            tags_raw.append(add_tag)
    if is_filtered_out_by_extra_tags(vi, tags_raw, Config.extra_tags, Config.id_sequence, vi.my_subfolder):
        Log.info(f'Info: video {sname} is filtered out by{" outer" if scenario is not None else ""} extra tags, skipping...')
        return DownloadResult.FAIL_SKIPPED
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
            vi.my_subfolder = matching_sq.subfolder
            vi.my_quality = matching_sq.quality
        elif utpalways_sq:
            vi.my_subfolder = utpalways_sq.subfolder
            vi.my_quality = utpalways_sq.quality
        else:
            Log.info(f'Info: unable to find matching or utp scenario subquery for {sname}, skipping...')
            return DownloadResult.FAIL_SKIPPED
    elif tdiv is None and len(Config.extra_tags) > 0 and Config.utp != DOWNLOAD_POLICY_ALWAYS:
        Log.warn(f'Warning: could not extract tags from {sname}, skipping due to untagged videos download policy...')
        return DownloadResult.FAIL_SKIPPED
    if Config.save_tags:
        vi.my_tags = ' '.join(tag.replace(' ', '_') for tag in tags_raw)
    if Config.save_descriptions or Config.save_comments:
        cidivs = a_html.find_all('div', class_='comment-body')
        cudivs = [cidiv.find('a', class_='comment-username') for cidiv in cidivs] if cidivs else []
        ctdivs = [cidiv.find('div', class_='comment-text') for cidiv in cidivs] if cidivs else []
        my_uploader = my_author or 'unknown'
        has_description = (cudivs[-1].text.lower() == my_uploader) if cudivs else False  # first comment by uploader
        if Config.save_descriptions:
            desc_comment = (f'{cudivs[-1].text}:\n{ctdivs[-1].text.strip()}') if has_description else ''
            desc_base = ''
            vi.my_description = desc_base or (f'\n{desc_comment}\n' if desc_comment else '')
        if Config.save_comments:
            comments_list = [f'{cudivs[i].text}:\n{ctdivs[i].text.strip()}' for i in range(len(ctdivs) - int(has_description))]
            vi.my_comments = ('\n' + '\n\n'.join(comments_list) + '\n') if comments_list else ''
    my_tags = filtered_tags(tags_raw) or my_tags

    nm_ = PREFIX if has_naming_flag(NamingFlags.PREFIX) else ''
    fname_part2 = extract_ext(vi.my_link)
    my_score = (f'{f"+" if score.isnumeric() else ""}{score}' if len(score) > 0
                else '' if len(rating) > 0 else 'unk')
    my_rating = (f'{", " if  len(my_score) > 0 else ""}{rating}{"%" if rating.isnumeric() else ""}' if len(rating) > 0
                 else '' if len(my_score) > 0 else 'unk')
    fname_part1 = (
        f'{nm_}{vi.my_id:d}'
        f'{f"_({my_score}{my_rating})" if has_naming_flag(NamingFlags.SCORE) else ""}'
        f'{f"_{vi.my_title}" if vi.my_title and has_naming_flag(NamingFlags.TITLE) else ""}'
    )
    # <fname_part1>_(<TAGS...>)_<QUALITY><fname_part2>
    extra_len = 2 + 2 + 5  # 2 underscores + 2 brackets + len('1080p') - max len of all qualities
    if has_naming_flag(NamingFlags.TAGS):
        while len(my_tags) > max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part1) + len(fname_part2) + extra_len)):
            my_tags = my_tags[:max(0, my_tags.rfind(TAGS_CONCAT_CHAR))]
        fname_part1 += f'_({my_tags})' if len(my_tags) > 0 else ''
    if len(my_tags) == 0 and len(fname_part1) > max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part2) + extra_len)):
        fname_part1 = fname_part1[:max(0, FULLPATH_MAX_BASE_LEN - (len(vi.my_folder) + len(fname_part2) + extra_len))]

    ret_vals = list()
    for i in range(QUALITIES.index(vi.my_quality), len(QUALITIES)):
        vi.my_link = f'{SITE}/media/videos/{QUALITY_STARTS[i]}{vi.my_id:d}{QUALITY_ENDS[i]}{fname_part2}'
        fname_mid = f'_{QUALITIES[i]}' if has_naming_flag(NamingFlags.QUALITY) else ''
        vi.my_filename = f'{fname_part1}{fname_mid}{fname_part2}'
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


async def check_video_download_status(vi: VideoInfo, init_size: int, resp: ClientResponse) -> None:
    dwn = VideoDownloadWorker.get()
    sname = vi.sname
    dest = vi.my_fullpath
    check_timer = float(DOWNLOAD_STATUS_CHECK_TIMER)
    slow_con_dwn_threshold = max(1, DOWNLOAD_STATUS_CHECK_TIMER * Config.throttle * Mem.KB)
    last_size = init_size
    try:
        while True:
            await sleep(check_timer)
            if not dwn.is_writing(dest):  # finished already
                Log.error(f'{sname} status checker is still running for finished download!')
                break
            file_size = stat(dest).st_size if path.isfile(dest) else 0
            if file_size < last_size + slow_con_dwn_threshold:
                last_speed = (file_size - last_size) / Mem.KB / DOWNLOAD_STATUS_CHECK_TIMER
                Log.warn(f'{sname} status check failed at {file_size:d} ({last_speed:.2f} KB/s)! Interrupting current try...')
                resp.connection.transport.abort()  # abort download task (forcefully - close connection)
                break
            last_size = file_size
    except CancelledError:
        pass


async def download_sceenshot(vi: VideoInfo, scr_num: int) -> DownloadResult:
    dwn = VideoDownloadWorker.get()
    sname = f'{PREFIX}{vi.my_id:d}_{scr_num:02d}.jpg'
    sfilename = f'{f"{vi.my_subfolder}/" if len(vi.my_subfolder) > 0 else ""}{PREFIX}{vi.my_id:d}/{scr_num:02d}.jpg'
    my_folder = f'{vi.my_folder}{PREFIX}{vi.my_id:d}/'
    fullpath = f'{my_folder}{scr_num:02d}.jpg'
    my_link = f'{SITE}/media/videos/tmb2/{vi.my_id:d}/{scr_num:d}.jpg'
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
    sname = vi.sname
    sfilename = f'{vi.my_sfolder}{vi.my_filename}'
    retries = 0
    ret = DownloadResult.SUCCESS
    skip = Config.dm == DOWNLOAD_MODE_SKIP
    status_checker = None  # type: Optional[Task]

    if skip is True:
        vi.set_state(VideoInfo.State.DONE)
        ret = DownloadResult.FAIL_SKIPPED
    else:
        vi.set_state(VideoInfo.State.DOWNLOADING)
        if not path.isdir(vi.my_folder):
            try:
                makedirs(vi.my_folder)
            except Exception:
                raise IOError(f'ERROR: Unable to create subfolder \'{vi.my_folder}\'!')
        else:
            nm_match = re_media_filename.match(vi.my_filename)
            nm_quality = nm_match.group(2)
            nm_curfile = file_already_exists(vi.my_id, nm_quality)
            if nm_curfile:
                if Config.continue_mode:
                    if nm_curfile != vi.my_fullpath:
                        Log.info(f'{sname} {vi.my_quality} (or similar) found. Enforcing new name (was \'{path.split(nm_curfile)[1]}\').')
                        rename(nm_curfile, vi.my_fullpath)
                else:
                    Log.info(f'{vi.my_filename} (or similar) already exists. Skipped.')
                    vi.set_state(VideoInfo.State.DONE)
                    return DownloadResult.FAIL_ALREADY_EXISTS

    while (not skip) and retries < CONNECT_RETRIES_BASE:
        try:
            if Config.dm == DOWNLOAD_MODE_TOUCH:
                Log.info(f'Saving<touch> {sname} {0.0:.2f} Mb to {sfilename}')
                with open(vi.my_fullpath, 'wb'):
                    vi.set_state(VideoInfo.State.DONE)
                break

            file_size = stat(vi.my_fullpath).st_size if path.isfile(vi.my_fullpath) else 0
            hkwargs = {'headers': {'Range': f'bytes={file_size:d}-'}} if file_size > 0 else {}  # type: Dict[str, Dict[str, str]]
            r = None
            async with await wrap_request(dwn.session, 'GET', vi.my_link, **hkwargs) as r:
                content_len = r.content_length or 0
                content_range_s = r.headers.get('Content-Range', '/').split('/', 1)
                content_range = int(content_range_s[1]) if len(content_range_s) > 1 and content_range_s[1].isnumeric() else 1
                if (content_len == 0 or r.status == 416) and file_size >= content_range:  # r.status may be 404 also (Apache mishap)
                    Log.warn(f'{sname} ({vi.my_quality}) is already completed, size: {file_size:d} ({file_size / Mem.MB:.2f} Mb)')
                    vi.set_state(VideoInfo.State.DONE)
                    break
                if r.status == 404:
                    Log.error(f'Got 404 for {sname}...!')
                    retries = CONNECT_RETRIES_BASE - 1
                    ret = DownloadResult.FAIL_NOT_FOUND
                if r.content_type and 'text' in r.content_type:
                    Log.error(f'File not found at {vi.my_link}!')
                    raise FileNotFoundError(vi.my_link)

                vi.my_expected_size = file_size + content_len
                vi.my_last_check_size = vi.my_start_size = file_size
                vi.my_last_check_time = vi.my_start_time = get_elapsed_time_i()
                starting_str = f' <continuing at {file_size:d}>' if file_size else ''
                total_str = f' / {vi.my_expected_size / Mem.MB:.2f}' if file_size else ''
                Log.info(f'Saving{starting_str} {sname} {content_len / Mem.MB:.2f}{total_str} Mb to {sfilename}')

                dwn.add_to_writes(vi)
                vi.set_state(VideoInfo.State.WRITING)
                status_checker = get_running_loop().create_task(check_video_download_status(vi, file_size, r))
                async with async_open(vi.my_fullpath, 'ab') as outf:
                    async for chunk in r.content.iter_chunked(1 * Mem.MB):
                        await outf.write(chunk)
                status_checker.cancel()
                dwn.remove_from_writes(vi)

                file_size = stat(vi.my_fullpath).st_size
                if vi.my_expected_size and file_size != vi.my_expected_size:
                    Log.error(f'Error: file size mismatch for {sfilename}: {file_size:d} / {vi.my_expected_size:d}')
                    raise IOError(vi.my_link)

                vi.set_state(VideoInfo.State.DONE)
                break
        except Exception as e:
            import sys
            print(sys.exc_info()[0], sys.exc_info()[1])
            if (r is None or r.status != 403) and isinstance(e, ClientPayloadError) is False:
                retries += 1
                Log.error(f'{sfilename}: error #{retries:d}...')
            if r is not None and r.closed is False:
                r.close()
            # Network error may be thrown before item is added to active downloads
            if dwn.is_writing(vi):
                dwn.remove_from_writes(vi)
            if status_checker is not None:
                status_checker.cancel()
            if retries < CONNECT_RETRIES_BASE:
                vi.set_state(VideoInfo.State.DOWNLOADING)
                await sleep(frand(1.0, 7.0))
            elif Config.keep_unfinished is False and path.isfile(vi.my_fullpath):
                Log.error(f'Failed to download {sfilename}. Removing unfinished file...')
                remove(vi.my_fullpath)

    ret = (ret if ret in (DownloadResult.FAIL_NOT_FOUND, DownloadResult.FAIL_SKIPPED) else
           DownloadResult.SUCCESS if retries < CONNECT_RETRIES_BASE else
           DownloadResult.FAIL_RETRIES)

    if Config.save_screenshots:
        sret = await download_sceenshots(vi)
        if sret != DownloadResult.SUCCESS:
            Log.warn(f'{sfilename}: `download_sceenshots()` has failed items (ret = {str(sret)})')

    return ret


def at_interrupt() -> None:
    dwn = VideoDownloadWorker.get()
    if dwn is not None:
        return dwn.at_interrupt()

#
#
#########################################
