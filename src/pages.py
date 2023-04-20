# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import sys
from asyncio import run as run_async, sleep
from re import search as re_search, compile as re_compile
from typing import List, Tuple, Optional, Any

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist_pages, read_cmdfile, is_parsed_cmdfile
from defs import (
    Log, MAX_VIDEOS_QUEUE_SIZE, ExtraConfig, SITE_PAGE_REQUEST_BASE, SLASH,
    HelpPrintExitException,
)
from download import DownloadWorker, at_interrupt
from path_util import prefilter_existing_items
from fetch_html import fetch_html
from scenario import DownloadScenario
from validators import find_and_resolve_config_conflicts

__all__ = ()

PAGE_ENTRY_RE = re_compile(r'^/video/(\d+)/[^/]+?$')


class VideoEntryBase:
    def __init__(self, m_id: int) -> None:
        self.my_id = m_id or 0

    def __eq__(self, other) -> bool:
        return self.my_id == other.my_id if isinstance(other, type(self)) else self.my_id == other if isinstance(other, int) else False


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
        while is_parsed_cmdfile(arglist):
            arglist = prepare_arglist_pages(read_cmdfile(arglist.path))
    except HelpPrintExitException:
        return
    except Exception:
        Log.fatal(f'\nUnable to parse cmdline. Exiting.\n{sys.exc_info()[0]}: {sys.exc_info()[1]}')
        return

    try:
        ExtraConfig.read_params(arglist)
        start_page = arglist.start  # type: int
        pages_count = arglist.pages  # type: int
        stop_id = arglist.stop_id  # type: int
        begin_id = arglist.begin_id  # type: int
        search_str = arglist.search  # type: str
        ds = arglist.download_scenario  # type: Optional[DownloadScenario]

        if find_and_resolve_config_conflicts(True, ds is not None) is True:
            await sleep(3.0)
    except Exception:
        Log.fatal('\nError reading parsed arglist!')
        return

    v_entries = []
    maxpage = 0

    pi = start_page
    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        while pi < start_page + pages_count:
            if pi > maxpage > 0:
                Log.info('reached parsed max page, page scan completed')
                break
            Log.info(f'page {pi:d}...{" (this is the last page!)" if 0 < maxpage == pi else ""}')

            a_html = await fetch_html(SITE_PAGE_REQUEST_BASE % (search_str, pi), session=s)
            if not a_html:
                Log.error(f'Error: cannot get html for page {pi:d}')
                continue

            pi += 1

            if maxpage == 0:
                for li_page in [li.find('a') for li in a_html.find_all('li', class_='hidden-xs')]:
                    try:
                        maxpage = max(maxpage, int(str(li_page.text)))
                    except Exception:
                        pass
                if maxpage == 0:
                    Log.info('Could not extract max page, assuming single page search')
                    maxpage = 1

            arefs = a_html.find_all('a', href=PAGE_ENTRY_RE)
            rrefs = a_html.find_all('b', string=re_compile(r'^(?:\d{1,3}%|-)$'))
            trefs = a_html.find_all('span', class_='video-title title-truncate m-t-5')
            assert len(arefs) == len(rrefs) == len(trefs)
            for refpair in zip(arefs, rrefs, trefs):
                cur_id = extract_id(refpair[0])
                if cur_id < stop_id:
                    Log.trace(f'skipping {cur_id:d} < {stop_id:d}')
                    continue
                if cur_id > begin_id:
                    Log.trace(f'skipping {cur_id:d} > {begin_id:d}')
                    continue
                href_rel = str(refpair[0].get('href'))
                tref = str(refpair[2].text)
                my_title = tref if tref != '' else href_rel[href_rel.rfind(SLASH) + 1:] if href_rel != '' else ''
                my_rating = str(refpair[1].text)
                v_entries.append(VideoEntryFull(cur_id, my_title, my_rating))

        orig_count = len(v_entries)
        minid, maxid = get_minmax_ids(v_entries)
        v_entries.reverse()
        prefilter_existing_items([v.my_id for v in v_entries])

        removed_count = orig_count - len(v_entries)

        if len(v_entries) == 0:
            if 0 < orig_count == removed_count:
                Log.fatal(f'\nAll {orig_count:d} videos already exist. Aborted.')
            else:
                Log.fatal('\nNo videos found. Aborted.')
            return

        Log.info(f'\nOk! {len(v_entries):d} videos found (+{removed_count:d} filtered), bound {minid:d} to {maxid:d}. Working...\n')

        await DownloadWorker(
            ((v.my_id, v.my_title, v.m_rate, ds) for v in v_entries),
            s).run()


async def run_main() -> None:
    await main()
    await sleep(0.5)


if __name__ == '__main__':
    assert sys.version_info >= (3, 7), 'Minimum python version required is 3.7!'
    try:
        run_async(run_main())
    except (KeyboardInterrupt, SystemExit):
        Log.warn('Warning: catched KeyboardInterrupt/SystemExit...')
        at_interrupt()
    exit(0)

#
#
#########################################
