# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import sleep
from os import path, stat, remove, makedirs, listdir
from random import uniform
from re import sub, search, match, compile as re_compile
from typing import List

from aiofile import async_open
from aiohttp import ClientSession

from defs import (
    __NM_DEBUG__, Log, CONNECT_RETRIES_ITEM, REPLACE_SYMBOLS, MAX_VIDEOS_QUEUE_SIZE, SITE_BASE, QUALITIES, QUALITY_STARTS, QUALITY_ENDS,
    SLASH, SITE_ITEM_REQUEST_BASE, TAGS_CONCAT_CHAR, DownloadResult, DOWNLOAD_POLICY_ALWAYS, DOWNLOAD_MODE_TOUCH
)
from fetch_html import get_proxy, fetch_html
from tagger import (
    filtered_tags, unite_separated_tags, get_matching_tag, get_or_group_matching_tag, is_neg_and_group_matches, register_item_tags,
)

NEWLINE = '\n'
re_nmfile = re_compile(fr'^nm_([^_]+)_.*?({"|".join(q for q in QUALITIES)})_py.+?$')
re_pdanger = re_compile(r'^This is a private video\..*?$')

downloads_queue = []  # type: List[int]
failed_items = []  # type: List[int]
total_queue_size = 0
total_queue_size_last = 0
download_queue_size_last = 0
id_sequence = []  # type: List[int]
current_ididx = 0


def register_id_sequence(id_seq: List[int]) -> None:
    global id_sequence
    global total_queue_size
    id_sequence = id_seq
    total_queue_size = len(id_sequence)


def is_queue_empty() -> bool:
    return len(downloads_queue) == 0


def is_queue_full() -> bool:
    return len(downloads_queue) >= MAX_VIDEOS_QUEUE_SIZE


def is_in_queue(idi: int) -> bool:
    return downloads_queue.count(idi) > 0


def normalize_filename(filename: str, dest_base: str) -> str:
    filename = sub(REPLACE_SYMBOLS, '_', filename)
    dest = dest_base.replace('\\', SLASH)
    if dest[-1] != SLASH:
        dest += SLASH
    dest += filename
    return dest


def extract_ext(href: str) -> str:
    try:
        return search(r'(\.[^&]{3,5})&', href).group(1)
    except Exception:
        return '.mp4'


async def try_register_in_queue(idi: int) -> bool:
    if is_in_queue(idi):
        if __NM_DEBUG__:
            Log(f'try_register_in_queue: {idi:d} is already in queue')
        return True
    elif not is_queue_full():
        downloads_queue.append(idi)
        if __NM_DEBUG__:
            Log(f'try_register_in_queue: {idi:d} added to queue')
        return True
    return False


async def try_unregister_from_queue(idi: int) -> None:
    global total_queue_size
    try:
        downloads_queue.remove(idi)
        total_queue_size -= 1
        if __NM_DEBUG__:
            Log(f'try_unregister_from_queue: {idi:d} removed from queue')
    except (ValueError,):
        if __NM_DEBUG__:
            Log(f'try_unregister_from_queue: {idi:d} was not in queue')


async def report_total_queue_size_callback(base_sleep_time: float) -> None:
    global total_queue_size_last
    global download_queue_size_last
    while total_queue_size > 0:
        wait_time = base_sleep_time if total_queue_size > 1 else 1.0
        await sleep(wait_time)
        downloading_count = len(downloads_queue)
        queue_size = total_queue_size - downloading_count
        if total_queue_size_last != queue_size or (queue_size == 0 and download_queue_size_last != downloading_count):
            Log(f'[Queue] items left: {queue_size} (downloading: {downloading_count})')
            total_queue_size_last = queue_size
            download_queue_size_last = downloading_count


async def download_id(idi: int, my_title: str, my_rating: str, dest_base: str, quality: str,
                      extra_tags: List[str], unlisted_policy: str, download_mode: str, save_tags: bool, session: ClientSession) -> None:
    global current_ididx

    while id_sequence[current_ididx] != idi:
        await sleep(min(10.0, 0.2 * abs(id_sequence.index(idi) - current_ididx)))

    while not await try_register_in_queue(idi):
        await sleep(uniform(2.0, 4.0))

    current_ididx += 1

    my_tags = 'no_tags'
    likes = ''
    i_html = await fetch_html(SITE_ITEM_REQUEST_BASE % idi)
    if i_html:
        if any('Error' in [d.string, d.text] for d in i_html.find_all('legend')):
            Log(f'Warning: Got error 404 for id {idi:d} (may be unlisted), likes will not be extracted...')
        elif any(re_pdanger.match(d.text) for d in i_html.find_all('div', class_='text-danger')):
            Log(f'Warning: Got private video error for id {idi:d}, likes/extra_title will not be extracted...')

        try:
            my_title = i_html.find('meta', attrs={'name': 'description'}).get('content')
        except Exception:
            Log(f'Warning: could not find description section for id {idi:d}...')
        try:
            keywords = str(i_html.find('meta', attrs={'name': 'keywords'}).get('content'))
            keywords = unite_separated_tags(keywords.replace(', ', TAGS_CONCAT_CHAR).lower())
            tags_raw = [tag.replace(' ', '_') for tag in keywords.split(TAGS_CONCAT_CHAR)]
            if len(extra_tags) > 0:
                for extag in extra_tags:
                    suc = True
                    if extag[0] == '(':
                        if get_or_group_matching_tag(extag, tags_raw) is None:
                            suc = False
                            Log(f'Video \'nm_{idi:d}.mp4\' misses required tag matching \'{extag}\'. Skipped!')
                    elif extag.startswith('-('):
                        if is_neg_and_group_matches(extag, tags_raw):
                            suc = False
                            Log(f'Video \'nm_{idi:d}.mp4\' contains excluded tags combination \'{extag[1:]}\'. Skipped!')
                    else:
                        mtag = get_matching_tag(extag[1:], tags_raw)
                        if mtag is not None and extag[0] == '-':
                            suc = False
                            Log(f'Video \'nm_{idi:d}.mp4\' contains excluded tag \'{mtag}\'. Skipped!')
                        elif mtag is None and extag[0] == '+':
                            suc = False
                            Log(f'Video \'nm_{idi:d}.mp4\' misses required tag matching \'{extag[1:]}\'. Skipped!')
                    if suc is False:
                        return await try_unregister_from_queue(idi)
            if save_tags:
                register_item_tags(idi, ' '.join(tag.replace(' ', '_') for tag in tags_raw))
            tags_str = filtered_tags(tags_raw)
            if tags_str != '':
                my_tags = tags_str
        except Exception:
            if len(extra_tags) > 0 and unlisted_policy != DOWNLOAD_POLICY_ALWAYS:
                Log(f'Warning: could not extract tags from id {idi:d}, skipping due to untagged videos download policy...')
                return await try_unregister_from_queue(idi)
            Log(f'Warning: could not extract tags from id {idi:d}...')
        try:
            dislikes_int = int(i_html.find('span', id='video_dislikes').text)
            likes_int = int(i_html.find('span', id='video_likes').text)
            likes_int -= dislikes_int
            likes = f'{"+" if likes_int > 0 else ""}{likes_int:d}'
        except Exception:
            pass

    # qlist = [QUALITIES.copy(), QUALITY_STARTS.copy(), QUALITY_ENDS.copy()]
    #
    # for i in range(len(qlist)):
    #     qlist[i].reverse()
    #
    # index = qlist[0].index(quality)
    #
    # for i, q in enumerate(qlist):
    #     qv = q[index]
    #     q.remove(qv)
    #     qlist[i] = [qv] + q
    #
    # qs = qlist[0]
    # qss = qlist[1]
    # qes = qlist[2]
    #
    # for i in range(qs.index(quality), len(qs)):
    #     link = SITE_BASE + '/media/videos/' + qss[i] + str(idi) + qes[i] + '.mp4'
    #     filename = 'nm_' + str(idi) + ('_' + my_title if my_title != '' else '') + '_' + qs[i] + '_pydw.mp4'
    #     if await download_file(idi, filename, dest_base, link, session):
    #         return

    my_score = likes if len(likes) > 0 else my_rating if len(my_rating) > 1 else 'unk'
    fname_part1 = f'nm_{idi:d}_score({my_score}){f"_{my_title}" if my_title != "" else ""}'
    fname_part2 = 'pydw.mp4'
    extra_len = 5 + 3 + 2  # 3 underscores + 2 brackets + len('1080p') - max len of all qualities
    while len(my_tags) > max(0, 240 - (len(dest_base) + len(fname_part1) + len(fname_part2) + extra_len)):
        my_tags = my_tags[:max(0, my_tags.rfind(TAGS_CONCAT_CHAR))]
    if len(my_tags) == 0 and len(fname_part1) > max(0, 240 - (len(dest_base) + len(fname_part2) + extra_len)):
        fname_part1 = fname_part1[:max(0, 240 - (len(dest_base) + len(fname_part2) + extra_len))]

    ret_vals = []  # type: List[int]
    for i in range(QUALITIES.index(quality), len(QUALITIES)):
        link = f'{SITE_BASE}/media/videos/{QUALITY_STARTS[i]}{idi:d}{QUALITY_ENDS[i]}.mp4'
        filename = f'{fname_part1}_({my_tags})_{QUALITIES[i]}_{fname_part2}'
        res = await download_file(idi, filename, dest_base, link, download_mode, session, True)
        if res not in [DownloadResult.DOWNLOAD_SUCCESS, DownloadResult.DOWNLOAD_FAIL_ALREADY_EXISTS]:
            ret_vals.append(res)
        else:
            return await try_unregister_from_queue(idi)

    for retval in ret_vals:
        if retval != DownloadResult.DOWNLOAD_FAIL_NOT_FOUND:
            failed_items.append(idi)
            break

    return await try_unregister_from_queue(idi)


async def download_file(idi: int, filename: str, dest_base: str, link: str, download_mode: str, s: ClientSession, from_ids=False) -> int:
    dest = normalize_filename(filename, dest_base)
    file_size = 0
    retries = 0
    ret = DownloadResult.DOWNLOAD_SUCCESS

    if not path.exists(dest_base):
        try:
            makedirs(dest_base)
        except Exception:
            raise IOError('ERROR: Unable to create subfolder!')
    else:
        # to check if file already exists we only take into account id and quality
        nm_match = match(re_nmfile, filename)
        nm_id = nm_match.group(1)
        nm_quality = nm_match.group(2)
        for fname in listdir(dest_base):
            try:
                f_match = match(re_nmfile, fname)
                f_id = f_match.group(1)
                f_quality = f_match.group(2)
                if nm_id == f_id and nm_quality == f_quality:
                    Log(f'{filename} (or similar) already exists. Skipped.')
                    if from_ids is False:
                        await try_unregister_from_queue(idi)
                    return DownloadResult.DOWNLOAD_FAIL_ALREADY_EXISTS
            except Exception:
                continue

    while not await try_register_in_queue(idi):
        await sleep(1.0)

    # delay first batch just enough to not make anyone angry
    # we need this when downloading many small files (previews)
    await sleep(1.0 - min(0.9, 0.1 * len(downloads_queue)))

    # filename_short = 'nm_' + str(idi)
    # Log('Retrieving %s...' % filename_short)
    while (not (path.exists(dest) and file_size > 0)) and retries < CONNECT_RETRIES_ITEM:
        try:
            if download_mode == DOWNLOAD_MODE_TOUCH:
                Log(f'Saving<touch> {0.0:.2f} Mb to {filename}')
                with open(dest, 'wb'):
                    pass
                break

            r = None
            async with s.request('GET', link, timeout=7200, proxy=get_proxy()) as r:
                if r.status == 404:
                    Log(f'Got 404 for {idi:d}...!')
                    retries = CONNECT_RETRIES_ITEM - 1
                    ret = DownloadResult.DOWNLOAD_FAIL_NOT_FOUND
                if r.content_type and r.content_type.find('text') != -1:
                    Log(f'File not found at {link}!')
                    raise FileNotFoundError(link)

                expected_size = r.content_length
                Log(f'Saving {(r.content_length / (1024.0 * 1024.0)) if r.content_length else 0.0:.2f} Mb to {filename}')

                async with async_open(dest, 'wb') as outf:
                    async for chunk in r.content.iter_chunked(2**20):
                        await outf.write(chunk)

                file_size = stat(dest).st_size
                if expected_size and file_size != expected_size:
                    Log(f'Error: file size mismatch for {filename}: {file_size:d} / {expected_size:d}')
                    raise IOError
                break
        except (KeyboardInterrupt,):
            assert False
        except (Exception,):
            import sys
            print(sys.exc_info()[0], sys.exc_info()[1])
            retries += 1
            Log(f'{filename}: error #{retries:d}...')
            if r:
                r.close()
            if path.exists(dest):
                remove(dest)
            await sleep(1)
            continue

    # delay next file if queue is full
    if len(downloads_queue) == MAX_VIDEOS_QUEUE_SIZE:
        await sleep(0.25)

    ret = (ret if ret == DownloadResult.DOWNLOAD_FAIL_NOT_FOUND else
           DownloadResult.DOWNLOAD_SUCCESS if retries < CONNECT_RETRIES_ITEM else
           DownloadResult.DOWNLOAD_FAIL_RETRIES)
    if from_ids is False:
        await try_unregister_from_queue(idi)
    return ret


async def after_download() -> None:
    if not is_queue_empty():
        Log('queue is not empty at exit!')

    if total_queue_size != 0:
        Log(f'total queue is still at {total_queue_size} != 0!')

    if len(failed_items) > 0:
        Log(f'Failed items:\n{NEWLINE.join(str(fi) for fi in sorted(failed_items))}')

#
#
#########################################