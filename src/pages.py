# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import sys
from asyncio import run as run_async, as_completed, sleep, get_running_loop
from re import search as re_search, compile as re_compile
from typing import List, Any, Tuple

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist_pages
from defs import (
    Log, SITE_PAGE_REQUEST_BASE, DEFAULT_HEADERS, MAX_VIDEOS_QUEUE_SIZE, SLASH, DOWNLOAD_MODE_FULL, DOWNLOAD_POLICY_DEFAULT
)
from download import download_id, is_queue_empty, after_download, report_total_queue_size_callback, register_id_sequence, set_verbosity
from fetch_html import fetch_html, set_proxy
from tagger import init_tags_files, dump_item_tags


PAGE_ENTRY_RE = re_compile(r'^/video/(\d+)/[^/]+?$')


class VideoEntryBase:
    def __init__(self, m_id: int) -> None:
        self.my_id = m_id or 0


class VideoEntryFull(VideoEntryBase):
    def __init__(self, m_id: int, m_title: str, my_rating: str) -> None:
        super().__init__(m_id)
        self.my_title = m_title or ''
        self.m_rate = my_rating or ''

    def __str__(self) -> str:
        return f'{self.my_id:d}: {self.my_title}'


def extract_id(aref: Any) -> int:
    return int(re_search(PAGE_ENTRY_RE, str(aref.get('href'))).group(1))


def get_minmax_ids(entry_list: List[VideoEntryBase]) -> Tuple[int, int]:
    minid = 0
    maxid = 0
    for entry in entry_list:
        if entry.my_id == 0:
            continue
        if entry.my_id > maxid:
            maxid = entry.my_id
        if entry.my_id < minid or minid == 0:
            minid = entry.my_id

    return minid, maxid


async def main() -> None:
    try:
        arglist = prepare_arglist_pages(sys.argv[1:])
    except Exception:
        Log('\nUnable to parse cmdline. Exiting...')
        return

    try:
        dest_base = arglist.path
        start_page = arglist.start
        pages_count = arglist.pages
        stop_id = arglist.stop_id
        begin_id = arglist.begin_id
        search_str = arglist.search
        quality = arglist.quality
        up = arglist.unli_video_policy
        dm = arglist.download_mode
        st = arglist.dump_tags
        ex_tags = arglist.extra_tags
        ds = arglist.download_scenario
        set_proxy(arglist.proxy if hasattr(arglist, 'proxy') else None)
        set_verbosity(arglist.verbose)

        delay_for_message = False
        if ds:
            if up != DOWNLOAD_POLICY_DEFAULT:
                Log('Info: running download script, outer unlisted policy will be ignored')
                up = DOWNLOAD_POLICY_DEFAULT
                delay_for_message = True
            if len(ex_tags) > 0:
                Log(f'Info: running download script: outer extra tags: {str(ex_tags)}')
                delay_for_message = True

        if delay_for_message:
            await sleep(3.0)
    except Exception:
        Log('\nError reading parsed arglist!')
        return

    v_entries = []
    maxpage = 0

    pi = start_page
    while pi < start_page + pages_count:
        if pi > maxpage > 0:
            Log('reached parsed max page, page scan completed')
            break
        Log(f'page {pi:d}...{" (this is the last page!)" if 0 < maxpage == pi else ""}')

        a_html = await fetch_html(SITE_PAGE_REQUEST_BASE % (search_str, pi))
        if not a_html:
            Log(f'cannot get html for page {pi:d}')
            continue

        pi += 1

        if maxpage == 0:
            lis = a_html.find_all('li', class_='hidden-xs')
            li_pages = [li.find('a') for li in lis]
            for li_page in li_pages:
                try:
                    page_num = int(str(li_page.text))
                    maxpage = max(maxpage, page_num)
                except Exception:
                    pass

        arefs = a_html.find_all('a', href=PAGE_ENTRY_RE)
        rrefs = a_html.find_all('b', string=re_compile(r'^(?:\d{1,3}%|-)$'))
        trefs = a_html.find_all('span', class_='video-title title-truncate m-t-5')
        assert len(arefs) == len(rrefs) == len(trefs)
        for refpair in zip(arefs, rrefs, trefs):
            cur_id = extract_id(refpair[0])
            if cur_id < stop_id:
                Log(f'skipping {cur_id:d} < {stop_id:d}')
                continue
            if cur_id > begin_id:
                Log(f'skipping {cur_id:d} > {begin_id:d}')
                continue
            href_rel = str(refpair[0].get('href'))
            tref = refpair[2].text
            my_title = tref if tref != '' else href_rel[href_rel.rfind(SLASH) + 1:] if href_rel != '' else ''
            my_rating = str(refpair[1].text)
            v_entries.append(VideoEntryFull(cur_id, my_title, my_rating))

    if len(v_entries) == 0:
        Log('\nNo videos found. Aborted.')
        return

    minid, maxid = get_minmax_ids(v_entries)
    Log(f'\nOk! {len(v_entries):d} videos found, bound {minid:d} to {maxid:d}. Working...\n')
    v_entries = list(reversed(v_entries))
    if st:
        init_tags_files(dest_base)
    register_id_sequence([v.my_id for v in v_entries])
    reporter = get_running_loop().create_task(report_total_queue_size_callback(3.0 if dm == DOWNLOAD_MODE_FULL else 1.0))
    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        s.headers.update(DEFAULT_HEADERS.copy())
        for cv in as_completed(
                [download_id(v.my_id, v.my_title, v.m_rate, dest_base, quality, ds, ex_tags, up, dm, st, s) for v in v_entries]):
            await cv
    await reporter

    if st:
        dump_item_tags()

    if not is_queue_empty():
        Log('pages: queue is not empty at exit!')

    await after_download()


async def run_main() -> None:
    await main()
    await sleep(0.5)


if __name__ == '__main__':
    assert sys.version_info >= (3, 7), 'Minimum python version required is 3.7!'
    run_async(run_main())
    exit(0)

#
#
#########################################
