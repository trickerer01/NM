# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import sleep, as_completed, Queue as AsyncQueue
from os import path, stat, remove, makedirs
from random import uniform as frand
from re import match
from typing import List, Optional, Union, Coroutine, Tuple

from aiofile import async_open
from aiohttp import ClientSession, TCPConnector

from defs import (
    CONNECT_RETRIES_ITEM, MAX_VIDEOS_QUEUE_SIZE, TAGS_CONCAT_CHAR, SITE, QUALITIES, QUALITY_STARTS, QUALITY_ENDS, SITE_ITEM_REQUEST_BASE,
    DownloadResult, DOWNLOAD_POLICY_ALWAYS, DOWNLOAD_MODE_TOUCH, NamingFlags, calc_sleep_time,
    Log, ExtraConfig, normalize_path, normalize_filename, get_elapsed_time_s, has_naming_flag, prefixp, LoggingFlags,
    re_nmfile, re_pdanger,
)
from fetch_html import fetch_html, wrap_request
from path_util import file_exists_in_folder
from scenario import DownloadScenario
from tagger import (
    filtered_tags, get_matching_tag, get_or_group_matching_tag, is_neg_and_group_matches, register_item_tags, dump_item_tags,
    unite_separated_tags,
)

__all__ = ('DownloadWorker', 'at_interrupt')

download_worker = None  # type: Optional[DownloadWorker]


class DownloadWorker:
    params_first_type = Tuple[int, str, str, Optional[DownloadScenario]]  # download_id
    params_second_type = params_first_type
    sequence_type = Tuple[Union[params_first_type, params_second_type]]  # Tuple here makes sure argument is not an empty list

    def __init__(self, my_sequence: sequence_type, session: ClientSession = None) -> None:
        self._func = download_id
        self._seq = list(my_sequence)
        self._queue = AsyncQueue(MAX_VIDEOS_QUEUE_SIZE)  # type: AsyncQueue[Tuple[int, Coroutine]]
        self.session = session

        self._downloads_active = []  # type: List[int]
        self.writes_active = []  # type: List[str]
        self.failed_items = []  # type: List[int]

        self._total_queue_size_last = 0
        self._download_queue_size_last = 0
        self._write_queue_size_last = 0

        global download_worker
        assert download_worker is None
        download_worker = self

    async def _at_task_start(self, idi: int) -> None:
        self._downloads_active.append(idi)
        Log.trace(f'[queue] {prefixp()}{idi:d}.mp4 added to queue')

    async def _at_task_finish(self, idi: int) -> None:
        self._downloads_active.remove(idi)
        Log.trace(f'[queue] {prefixp()}{idi:d}.mp4 removed from queue')

    async def _prod(self) -> None:
        while len(self._seq) > 0:
            if self._queue.full() is False:
                await self._queue.put((int(self._seq[0][0]), self._func(*self._seq[0])))
                del self._seq[0]
            else:
                await sleep(0.2)

    async def _cons(self) -> None:
        while len(self._seq) + self._queue.qsize() > 0:
            if self._queue.empty() is False and len(self._downloads_active) < MAX_VIDEOS_QUEUE_SIZE:
                idi, task = await self._queue.get()
                await self._at_task_start(idi)
                await task
                await self._at_task_finish(idi)
                self._queue.task_done()
            else:
                await sleep(0.25)

    async def _report_total_queue_size_callback(self, base_sleep_time: float) -> None:
        while len(self._seq) + self._queue.qsize() + len(self._downloads_active) > 0:
            await sleep(base_sleep_time if len(self._seq) + self._queue.qsize() > 0 else 1.0)
            queue_size = len(self._seq) + self._queue.qsize()
            download_count = len(self._downloads_active)
            write_count = len(self.writes_active)
            queue_last = self._total_queue_size_last
            downloading_last = self._download_queue_size_last
            write_last = self._write_queue_size_last
            if queue_last != queue_size or downloading_last != download_count or write_last != write_count:
                Log.info(f'[{get_elapsed_time_s()}] queue: {queue_size:d}, downloading: {download_count:d} (writing: {write_count:d})')
                self._total_queue_size_last = queue_size
                self._download_queue_size_last = download_count
                self._write_queue_size_last = write_count

    async def _after_download(self) -> None:
        newline = '\n'
        if len(self._seq) != 0:
            Log.fatal(f'total queue is still at {len(self._seq):d} != 0!')
        if len(self.writes_active) > 0:
            Log.fatal(f'active writes count is still at {len(self.writes_active):d} != 0!')
        if len(self.failed_items) > 0:
            Log.fatal(f'Failed items:\n{newline.join(str(fi) for fi in sorted(self.failed_items))}')

    async def run(self) -> None:
        async with self.session or ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as self.session:
            workers = [self._report_total_queue_size_callback(calc_sleep_time(3.0)), self._prod()]
            for _ in range(MAX_VIDEOS_QUEUE_SIZE):
                workers.append(self._cons())
            for cv in as_completed(workers):
                await cv
        if ExtraConfig.save_tags is True:
            dump_item_tags()
        await self._after_download()


def is_filtered_out_by_extra_tags(idi: int, tags_raw: List[str], extra_tags: List[str], subfolder: str) -> bool:
    suc = True
    if len(extra_tags) > 0:
        for extag in extra_tags:
            if extag[0] == '(':
                if get_or_group_matching_tag(extag, tags_raw) is None:
                    suc = False
                    Log.trace(f'[{subfolder}] Video \'{prefixp()}{idi:d}.mp4\' misses required tag matching \'{extag}\'. Skipped!',
                              LoggingFlags.LOGGING_EX_MISSING_TAGS)
            elif extag.startswith('-('):
                if is_neg_and_group_matches(extag, tags_raw):
                    suc = False
                    Log.info(f'[{subfolder}] Video \'{prefixp()}{idi:d}.mp4\' contains excluded tags combination \'{extag[1:]}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
            else:
                my_extag = extag[1:] if extag[0] == '-' else extag
                mtag = get_matching_tag(my_extag, tags_raw)
                if mtag is not None and extag[0] == '-':
                    suc = False
                    Log.info(f'[{subfolder}] Video \'{prefixp()}{idi:d}.mp4\' contains excluded tag \'{mtag}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
                elif mtag is None and extag[0] != '-':
                    suc = False
                    Log.trace(f'[{subfolder}] Video \'{prefixp()}{idi:d}.mp4\' misses required tag matching \'{my_extag}\'. Skipped!',
                              LoggingFlags.LOGGING_EX_MISSING_TAGS)
    return not suc


def get_matching_scenario_subquery_idx(idi: int, tags_raw: List[str], likes: str, scenario: DownloadScenario) -> int:
    for idx, sq in enumerate(scenario.queries):
        if not is_filtered_out_by_extra_tags(idi, tags_raw, sq.extra_tags, sq.subfolder):
            if len(likes) > 0:
                try:
                    if int(likes) < sq.minscore:
                        Log.info(f'[{sq.subfolder}] Video \'{prefixp()}{idi:d}.mp4\''
                                 f' has low score \'{int(likes):d}\' (required {sq.minscore:d})!',
                                 LoggingFlags.LOGGING_EX_LOW_SCORE)
                        continue
                except Exception:
                    pass
            return idx
    return -1


def get_uvp_always_subquery_idx(scenario: DownloadScenario) -> int:
    for idx, sq in enumerate(scenario.queries):
        if sq.uvp == DOWNLOAD_POLICY_ALWAYS:
            return idx
    return -1


async def download_id(idi: int, my_title: str, my_rating: str, scenario: Optional[DownloadScenario]) -> None:
    my_subfolder = ''
    my_quality = ExtraConfig.quality
    my_tags = 'no_tags'
    likes = ''
    i_html = await fetch_html(SITE_ITEM_REQUEST_BASE % idi, session=download_worker.session)
    if i_html:
        if any('Error' in [d.string, d.text] for d in i_html.find_all('legend')):
            Log.error(f'Warning: Got error 404 for {prefixp()}{idi:d}.mp4 (may be unlisted), author/likes will not be extracted...')
        elif any(re_pdanger.match(d.text) for d in i_html.find_all('div', class_='text-danger')):
            Log.warn(f'Warning: Got private video error for {prefixp()}{idi:d}.mp4, likes/extra_title will not be extracted...')

        try:
            my_title = i_html.find('meta', attrs={'name': 'description'}).get('content')
        except Exception:
            Log.warn(f'Warning: could not find description section for {prefixp()}{idi:d}.mp4...')
        try:
            dislikes_int = int(i_html.find('span', id='video_dislikes').text)
            likes_int = int(i_html.find('span', id='video_likes').text)
            likes_int -= dislikes_int
            likes = f'{"+" if likes_int > 0 else ""}{likes_int:d}'
        except Exception:
            pass
        try:
            try:
                my_author = str(i_html.find('div', class_='pull-left user-container').find('span').string).lower()
            except Exception:
                my_author = i_html.find('div', class_='text-danger').find('a').string.lower()
        except Exception:
            Log.warn(f'Warning: cannot extract author for {prefixp()}{idi:d}.mp4.')
            my_author = ''
        try:
            keywords = str(i_html.find('meta', attrs={'name': 'keywords'}).get('content'))
            keywords = unite_separated_tags(keywords.replace(', ', TAGS_CONCAT_CHAR).lower())
            tags_raw = [tag.replace(' ', '_') for tag in keywords.split(TAGS_CONCAT_CHAR)]
            for add_tag in [ca for ca in [my_author] if len(ca) > 0]:
                if add_tag not in tags_raw:
                    tags_raw.append(add_tag)
            if is_filtered_out_by_extra_tags(idi, tags_raw, ExtraConfig.extra_tags, my_subfolder):
                Log.info(f'Info: video {prefixp()}{idi:d}.mp4 is filtered out by outer extra tags, skipping...')
                return
            if len(likes) > 0:
                try:
                    if int(likes) < ExtraConfig.min_score:
                        Log.info(f'Info: video {prefixp()}{idi:d}.mp4 '
                                 f'has low score \'{int(likes):d}\' (required {ExtraConfig.min_score:d}), skipping...')
                        return
                except Exception:
                    pass
            if scenario is not None:
                sub_idx = get_matching_scenario_subquery_idx(idi, tags_raw, likes, scenario)
                if sub_idx == -1:
                    Log.info(f'Info: unable to find matching scenario subquery for {prefixp()}{idi:d}.mp4, skipping...')
                    return
                my_subfolder = scenario.queries[sub_idx].subfolder
                my_quality = scenario.queries[sub_idx].quality
            if ExtraConfig.save_tags:
                register_item_tags(idi, ' '.join(tag.replace(' ', '_') for tag in tags_raw), my_subfolder)
            tags_str = filtered_tags(tags_raw)
            if tags_str != '':
                my_tags = tags_str
        except Exception:
            if scenario is not None:
                uvp_idx = get_uvp_always_subquery_idx(scenario)
                if uvp_idx == -1:
                    Log.warn(f'Warning: could not extract tags from {prefixp()}{idi:d}.mp4, '
                             f'skipping due to unlisted videos download policy (scenario)...')
                    return
                my_subfolder = scenario.queries[uvp_idx].subfolder
                my_quality = scenario.queries[uvp_idx].quality
            elif len(ExtraConfig.extra_tags) > 0 and ExtraConfig.uvp != DOWNLOAD_POLICY_ALWAYS:
                Log.warn(f'Warning: could not extract tags from {prefixp()}{idi:d}.mp4, skipping due to unlisted videos download policy...')
                return
            Log.warn(f'Warning: could not extract tags from {prefixp()}{idi:d}.mp4...')
    else:
        Log.error(f'Error: unable to retreive html for {prefixp()}{idi:d}.mp4! Aborted!')
        return

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
    #     link = SITE + '/media/videos/' + qss[i] + str(idi) + qes[i] + '.mp4'
    #     filename = 'nm_' + str(idi) + ('_' + my_title if my_title != '' else '') + '_' + qs[i] + '_pydw.mp4'
    #     if await download_file(idi, filename, dest_base, link, session):
    #         return

    my_dest_base = normalize_path(f'{ExtraConfig.dest_base}{my_subfolder}')
    my_score = likes if len(likes) > 0 else my_rating if len(my_rating) > 1 else 'unk'
    extra_len = 5 + 3 + 2  # 3 underscores + 2 brackets + len('1080p') - max len of all qualities
    fname_part2 = 'pydw.mp4'
    fname_part1 = (
        f'{prefixp() if has_naming_flag(NamingFlags.NAMING_FLAG_PREFIX) else ""}'
        f'{idi:d}'
        f'{f"_score({my_score})" if has_naming_flag(NamingFlags.NAMING_FLAG_SCORE) else ""}'
        f'{f"_{my_title}" if my_title != "" and has_naming_flag(NamingFlags.NAMING_FLAG_TITLE) else ""}'
    )
    if has_naming_flag(NamingFlags.NAMING_FLAG_TAGS):
        while len(my_tags) > max(0, 240 - (len(my_dest_base) + len(fname_part1) + len(fname_part2) + extra_len)):
            my_tags = my_tags[:max(0, my_tags.rfind(TAGS_CONCAT_CHAR))]
        fname_part1 = f'{fname_part1}{f"_({my_tags})" if len(my_tags) > 0 else ""}'

    if len(my_tags) == 0 and len(fname_part1) > max(0, 240 - (len(my_dest_base) + len(fname_part2) + extra_len)):
        fname_part1 = fname_part1[:max(0, 240 - (len(my_dest_base) + len(fname_part2) + extra_len))]

    ret_vals = []  # type: List[int]
    for i in range(QUALITIES.index(my_quality), len(QUALITIES)):
        link = f'{SITE}/media/videos/{QUALITY_STARTS[i]}{idi:d}{QUALITY_ENDS[i]}.mp4'
        filename = f'{fname_part1}_{QUALITIES[i]}_{fname_part2}'
        res = await download_file(idi, filename, my_dest_base, link, my_subfolder)
        if res not in [DownloadResult.DOWNLOAD_SUCCESS, DownloadResult.DOWNLOAD_FAIL_ALREADY_EXISTS]:
            ret_vals.append(res)
        else:
            return

    for retval in ret_vals:
        if retval != DownloadResult.DOWNLOAD_FAIL_NOT_FOUND:
            download_worker.failed_items.append(idi)
            break


async def download_file(idi: int, filename: str, my_dest_base: str, link: str, subfolder='') -> int:
    dest = normalize_filename(filename, my_dest_base)
    sfilename = f'{f"{subfolder}/" if len(subfolder) > 0 else ""}{filename}'
    file_size = 0
    retries = 0
    ret = DownloadResult.DOWNLOAD_SUCCESS

    if not path.isdir(my_dest_base):
        try:
            makedirs(my_dest_base)
        except Exception:
            raise IOError(f'ERROR: Unable to create subfolder \'{my_dest_base}\'!')
    else:
        nm_match = match(re_nmfile, filename)
        nm_quality = nm_match.group(2)
        if file_exists_in_folder(my_dest_base, idi, nm_quality, False):
            Log.info(f'{filename} (or similar) already exists. Skipped.')
            return DownloadResult.DOWNLOAD_FAIL_ALREADY_EXISTS

    # filename_short = 'nm_' + str(idi)
    # Log('Retrieving %s...' % filename_short)
    while (not (path.isfile(dest) and file_size > 0)) and retries < CONNECT_RETRIES_ITEM:
        try:
            if ExtraConfig.dm == DOWNLOAD_MODE_TOUCH:
                Log.info(f'Saving<touch> {0.0:.2f} Mb to {sfilename}')
                with open(dest, 'wb'):
                    pass
                break

            r = None
            async with await wrap_request(download_worker.session, 'GET', link, timeout=7200, headers={'Referer': link}) as r:
                if r.status == 404:
                    Log.error(f'Got 404 for {prefixp()}{idi:d}.mp4...!')
                    retries = CONNECT_RETRIES_ITEM - 1
                    ret = DownloadResult.DOWNLOAD_FAIL_NOT_FOUND
                if r.content_type and r.content_type.find('text') != -1:
                    Log.error(f'File not found at {link}!')
                    raise FileNotFoundError(link)

                expected_size = r.content_length
                Log.info(f'Saving {(r.content_length / (1024.0 * 1024.0)) if r.content_length else 0.0:.2f} Mb to {sfilename}')

                download_worker.writes_active.append(dest)
                async with async_open(dest, 'wb') as outf:
                    async for chunk in r.content.iter_chunked(2**20):
                        await outf.write(chunk)
                download_worker.writes_active.remove(dest)

                file_size = stat(dest).st_size
                if expected_size and file_size != expected_size:
                    Log.error(f'Error: file size mismatch for {sfilename}: {file_size:d} / {expected_size:d}')
                    raise IOError
                break
        except Exception:
            import sys
            print(sys.exc_info()[0], sys.exc_info()[1])
            retries += 1
            Log.error(f'{sfilename}: error #{retries:d}...')
            if r is not None:
                r.close()
            if path.isfile(dest):
                remove(dest)
            # Network error may be thrown before item is added to active download
            if dest in download_worker.writes_active:
                download_worker.writes_active.remove(dest)
            await sleep(frand(1.0, 7.0))
            continue

    ret = (ret if ret == DownloadResult.DOWNLOAD_FAIL_NOT_FOUND else
           DownloadResult.DOWNLOAD_SUCCESS if retries < CONNECT_RETRIES_ITEM else
           DownloadResult.DOWNLOAD_FAIL_RETRIES)
    return ret


def at_interrupt() -> None:
    if download_worker is None:
        return

    if len(download_worker.writes_active) > 0:
        Log.debug(f'at_interrupt: cleaning {len(download_worker.writes_active):d} unfinished files...')
        for unfinished in sorted(download_worker.writes_active):
            Log.debug(f'at_interrupt: trying to remove \'{unfinished}\'...')
            if path.isfile(unfinished):
                remove(unfinished)
            else:
                Log.debug(f'at_interrupt: file \'{unfinished}\' not found!')

#
#
#########################################
