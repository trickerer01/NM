# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import sys
from asyncio import run as run_async, sleep
from typing import Sequence

from cmdargs import HelpPrintExitException, prepare_arglist
from config import Config
from defs import (
    PREFIX, SITE_ITEM_REQUEST_SEARCH_PAGE, SITE_ITEM_REQUEST_UPLOADER_PAGE, SITE_ITEM_REQUEST_PLAYLIST_PAGE,
)
from download import download, at_interrupt
from fetch_html import make_session, fetch_html
from logger import Log
from path_util import prefilter_existing_items
from rex import re_page_entry
from util import at_startup
from validators import find_and_resolve_config_conflicts
from vinfo import VideoInfo, get_min_max_ids

__all__ = ('main_sync',)


async def main(args: Sequence[str]) -> None:
    try:
        arglist = prepare_arglist(args, True)
    except HelpPrintExitException:
        return

    Config.read(arglist, True)

    full_download = True
    video_ref_class = 'col-6 col-sm-6 col-md-4 col-lg-4 col-xl-3'

    if find_and_resolve_config_conflicts() is True:
        await sleep(3.0)

    def check_id_bounds(video_id: int) -> bool:
        if video_id > Config.end_id:
            Log.trace(f'skipping {video_id:d} > {Config.end_id:d}')
            return False
        if video_id < Config.start_id:
            Log.trace(f'skipping {video_id:d} < {Config.start_id:d}')
            return False
        return True

    v_entries = list()
    maxpage = Config.end if Config.start == Config.end else 0

    pi = Config.start
    async with make_session() as s:
        while pi <= Config.end:
            if pi > maxpage > 0:
                Log.info('reached parsed max page, page scan completed')
                break

            page_addr = (
                (SITE_ITEM_REQUEST_PLAYLIST_PAGE % (Config.playlist_name, pi)) if Config.playlist_name else
                (SITE_ITEM_REQUEST_UPLOADER_PAGE % (Config.uploader, pi)) if Config.uploader else
                (SITE_ITEM_REQUEST_SEARCH_PAGE % (Config.search, pi))
            )
            a_html = await fetch_html(page_addr, session=s)
            if not a_html:
                Log.error(f'Error: cannot get html for page {pi:d}')
                continue

            pi += 1

            if maxpage == 0 or pi - 1 == maxpage:
                old_maxpage = maxpage
                if Config.playlist_name and any('Error' in (d.string, d.text) for d in a_html.find_all('legend')):
                    Log.fatal(f'\nFatal: playlist is not found for user \'{Config.playlist_name}\'!')
                    return
                for a_page in a_html.find_all('a', class_='page-link'):
                    try:
                        maxpage = max(maxpage, int(str(a_page.text)))
                    except Exception:
                        pass
                if maxpage == 0:
                    Log.info('Could not extract max page, assuming single page search')
                    maxpage = 1
                elif old_maxpage == 0:
                    Log.debug(f'Extracted max page: {maxpage:d}')
                elif old_maxpage < maxpage:
                    Log.debug(f'Extracted new max page: {maxpage:d}')

            if Config.get_maxid:
                miref = a_html.find('div', class_=video_ref_class).find('a')
                max_id = re_page_entry.search(str(miref.get('href'))).group(1)
                Log.fatal(f'{PREFIX[:2].upper()}: {max_id}')
                return

            Log.info(f'page {pi - 1:d}...{" (this is the last page!)" if (0 < maxpage == pi - 1) else ""}')

            vrefs = a_html.find_all('div', class_=video_ref_class)
            for vref in vrefs:
                aref = vref.find_all('a')[-1]
                rref = vref.find('span', class_='content-rating')
                tref = aref.find('span')
                cur_id = int(re_page_entry.search(str(aref.get('href'))).group(1))
                if check_id_bounds(cur_id) is False:
                    continue
                my_title = str(tref.text)
                my_rating = str(rref.find('span').text) if rref else ''
                my_rating = '' if my_rating in ('0%', '') else my_rating[:-1]  # 0% rating doesn't mean all votes are dislikes necessarily
                v_entries.append(VideoInfo(cur_id, my_title, m_rating=my_rating))

        v_entries.reverse()
        orig_count = len(v_entries)

        if orig_count > 0:
            prefilter_existing_items(v_entries)

        removed_count = orig_count - len(v_entries)

        if orig_count == removed_count:
            if orig_count > 0:
                Log.fatal(f'\nAll {orig_count:d} videos already exist. Aborted.')
            else:
                Log.fatal('\nNo videos found. Aborted.')
            return

        minid, maxid = get_min_max_ids(v_entries)
        Log.info(f'\nOk! {len(v_entries):d} ids (+{removed_count:d} filtered out), bound {minid:d} to {maxid:d}. Working...\n')

        await download(v_entries, full_download, removed_count, s)


async def run_main(args: Sequence[str]) -> None:
    await main(args)
    await sleep(0.5)


def main_sync(args: Sequence[str]) -> None:
    assert sys.version_info >= (3, 7), 'Minimum python version required is 3.7!'

    try:
        run_async(run_main(args))
    except (KeyboardInterrupt, SystemExit):
        Log.warn('Warning: catched KeyboardInterrupt/SystemExit...')
    finally:
        at_interrupt()


if __name__ == '__main__':
    at_startup()
    main_sync(sys.argv[1:])
    exit(0)

#
#
#########################################
