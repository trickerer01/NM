# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import run as run_async, as_completed, sleep
from re import search as re_search, compile as re_compile
from sys import argv
from typing import List, Any, Tuple

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist_pages
from defs import Log, SITE_PAGE_REQUEST_BASE, DEFAULT_HEADERS, MAX_VIDEOS_QUEUE_SIZE, SLASH_CHAR
from download import download_id, is_queue_empty, failed_items
from fetch_html import fetch_html, set_proxy


PAGE_ENTRY_RE = re_compile(r'^/video/(\d{3,6})/[^/]+$')


class VideoEntryBase:
    def __init__(self, m_id: int) -> None:
        self.my_id = m_id or 0


class VideoEntryFull(VideoEntryBase):
    def __init__(self, m_id: int, m_title: str, my_rating: str) -> None:
        super().__init__(m_id)
        self.my_title = m_title or ''
        self.my_rating = my_rating or ''

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
        arglist = prepare_arglist_pages(argv[1:])
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
        quality = arglist.max_quality
        set_proxy(arglist.proxy if hasattr(arglist, 'proxy') else None)
    except Exception:
        Log('\nError reading parsed arglist!')
        return

    vid_entries = []
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
        rrefs = a_html.find_all('b', text=re_compile(r'^\d{1,3}%$'))
        assert len(arefs) == len(rrefs)
        for refpair in zip(arefs, rrefs):
            cur_id = extract_id(refpair[0])
            if cur_id < stop_id:
                Log(f'skipping {cur_id:d} < {stop_id:d}')
                continue
            if cur_id > begin_id:
                Log(f'skipping {cur_id:d} > {begin_id:d}')
                continue
            href_rel = str(refpair[0].get('href'))
            my_title = href_rel[href_rel.rfind(SLASH_CHAR) + 1:] if href_rel != '' else ''
            my_rating = f'{str(refpair[1].text)[:-1]}pct'
            vid_entries.append(VideoEntryFull(cur_id, my_title, my_rating))

    if len(vid_entries) == 0:
        Log('\nNo videos found. Aborted.')
        return

    minid, maxid = get_minmax_ids(vid_entries)
    Log(f'\nOk! {len(vid_entries):d} videos found, bound {minid:d} to {maxid:d}. Working...\n')
    vid_entries = list(reversed(vid_entries))
    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        s.headers.update(DEFAULT_HEADERS.copy())
        for cv in as_completed([download_id(v.my_id, v.my_title, v.my_rating, dest_base, quality, s) for v in vid_entries]):
            await cv

    if not is_queue_empty():
        Log('pages: queue is not empty at exit!')

    if len(failed_items) > 0:
        failed_items.sort()
        Log('Failed items:')
        for fi in failed_items:
            Log(' ', str(fi))


async def run_main() -> None:
    await main()
    await sleep(0.5)


if __name__ == '__main__':
    run_async(run_main())
    exit(0)

#
#
#########################################
