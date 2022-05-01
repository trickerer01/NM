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
from typing import List, Any

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist
from defs import Log, SITE_BASE, SITE_PAGE_REQUEST_BASE, DEFAULT_HEADERS, MAX_VIDEOS_QUEUE_SIZE, SLASH_CHAR
from download import download_id, is_queue_empty, failed_items
from fetch_html import fetch_html


PAGE_ENTRY_RE = re_compile(r'^/video/(\d{3,6})/[^/]+$')


class VideoEntryBase:
    def __init__(self, m_id: int):
        self.my_id = m_id or 0


class VideoEntryFull(VideoEntryBase):
    def __init__(self, m_id: int, m_href: str, m_title: str):
        super().__init__(m_id)
        self.my_href = m_href or ''
        self.my_title = m_title or ''

    def __str__(self):
        return str(self.my_id) + ': ' + str(self.my_title)


def extract_id(aref: Any) -> int:
    return int(re_search(PAGE_ENTRY_RE, str(aref.get('href'))).group(1))


def get_minmax_ids(entry_list: List[VideoEntryBase]) -> (int, int):
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
        arglist = prepare_arglist(argv[1:])
    except Exception:
        Log('\nUnable to parse cmdline. Exiting...')
        return

    try:
        dest_base = arglist.path
        start_page = arglist.start
        pages_count = arglist.pages
        stop_id = arglist.stop_id
        search_str = arglist.search
        quality = arglist.max_quality
    except Exception:
        Log('\nError reading parsed arglist!')
        return

    vid_entries = []
    maxpage = 0

    for pi in range(start_page, start_page + pages_count):
        if maxpage and pi > maxpage:
            Log('reached parsed max page, page scan completed')
            break
        Log(('page %d...%s' % (pi, ' (this is the last page!)' if maxpage and pi == maxpage else '')))

        a_html = await fetch_html(SITE_PAGE_REQUEST_BASE % (search_str, pi))
        if not a_html:
            Log('cannot get html for page %d', pi)
            continue

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
        for aref in arefs:
            cur_id = extract_id(aref)
            if cur_id < stop_id:
                Log('skipping %d < %d' % (cur_id, stop_id))
                continue
            href_rel = str(aref.get('href'))
            my_href = SITE_BASE + href_rel
            my_title = href_rel[href_rel.rfind(SLASH_CHAR) + 1:] if href_rel else ''
            vid_entries.append(VideoEntryFull(cur_id, my_href, my_title))

    if len(vid_entries) == 0:
        Log('\nNo videos found. Aborted.')
        return

    minid, maxid = get_minmax_ids(vid_entries)
    Log('\nOk! %d videos found, bound %d to %d. Working...\n' % (len(vid_entries), minid, maxid))
    vid_entries = list(reversed(vid_entries))
    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        s.headers.update(DEFAULT_HEADERS)
        for cv in as_completed([download_id(v.my_id, v.my_title, dest_base, quality, s) for v in vid_entries]):
            await cv

    if not is_queue_empty():
        Log('pages: queue is not empty at exit!')

    if len(failed_items) > 0:
        Log('Failed items:')
        for fi in failed_items:
            Log(' ', str(fi))


async def run_main():
    await main()
    await sleep(0.25)


if __name__ == '__main__':
    run_async(run_main())
    exit(0)

#
#
#########################################
