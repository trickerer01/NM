# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import sys
from asyncio import run as run_async, sleep
from re import compile as re_compile
from typing import Sequence

from cmdargs import prepare_arglist_pages, read_cmdfile, is_parsed_cmdfile
from defs import (
    Log, Config, SITE_ITEM_REQUEST_PAGE, SLASH, prefixp, LoggingFlags,
    HelpPrintExitException, SITE_ITEM_REQUEST_PLAYLIST_PAGE,
)
from download import download, at_interrupt
from path_util import prefilter_existing_items
from fetch_html import make_session, fetch_html
from validators import find_and_resolve_config_conflicts
from vinfo import VideoInfo

__all__ = ('main_sync',)


async def main(args: Sequence[str]) -> None:
    try:
        arglist = prepare_arglist_pages(args)
        while is_parsed_cmdfile(arglist):
            arglist = prepare_arglist_pages(read_cmdfile(arglist.path))
    except HelpPrintExitException:
        return
    except Exception:
        Log.fatal(f'\nUnable to parse cmdline. Exiting.\n{sys.exc_info()[0]}: {sys.exc_info()[1]}')
        return

    try:
        Config.read(arglist, True)
        search_str = arglist.search  # type: str
        playlist_name = arglist.playlist_name  # type: str

        full_download = True
        re_page_entry = re_compile(r'^/video/(\d+)/[^/]+?$')
        re_page_rating = re_compile(r'^(?:\d{1,3}%|-)$')
        re_page_title = re_compile(r'^video-title title-truncate.*$')

        if playlist_name and search_str:
            Log.fatal('\nError: cannot search within playlist! Please use one or the other')
            raise ValueError

        if Config.get_maxid:
            Config.logging_flags = LoggingFlags.LOGGING_FATAL
            Config.start = Config.end = Config.start_id = Config.end_id = 1

        if Config.start_id > Config.end_id:
            Log.fatal(f'\nError: invalid video id bounds: start ({Config.start_id:d}) > end ({Config.end_id:d})')
            raise ValueError

        if find_and_resolve_config_conflicts() is True:
            await sleep(3.0)
    except Exception:
        Log.fatal('\nError reading parsed arglist!')
        return

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
    async with await make_session() as s:
        while pi <= Config.end:
            if pi > maxpage > 0:
                Log.info('reached parsed max page, page scan completed')
                break
            Log.info(f'page {pi:d}...{" (this is the last page!)" if (0 < maxpage == pi) else ""}')

            page_addr = (
                (SITE_ITEM_REQUEST_PLAYLIST_PAGE % (playlist_name, pi)) if playlist_name else
                (SITE_ITEM_REQUEST_PAGE % (search_str, pi))
            )
            a_html = await fetch_html(page_addr, session=s)
            if not a_html:
                Log.error(f'Error: cannot get html for page {pi:d}')
                continue

            pi += 1

            if maxpage == 0:
                if playlist_name and any('Error' in (d.string, d.text) for d in a_html.find_all('legend')):
                    Log.fatal(f'\nFatal: playlist is not found for user \'{playlist_name}\'!')
                    return
                for li_page in [li.find('a') for li in a_html.find_all('li', class_='hidden-xs')]:
                    try:
                        maxpage = max(maxpage, int(str(li_page.text)))
                    except Exception:
                        pass
                if maxpage == 0:
                    Log.info('Could not extract max page, assuming single page search')
                    maxpage = 1

            if Config.get_maxid:
                miref = a_html.find('a', href=re_page_entry)
                max_id = re_page_entry.search(str(miref.get('href'))).group(1)
                Log.fatal(f'{prefixp()[:2].upper()}: {max_id}')
                return

            arefs = a_html.find_all('a', href=re_page_entry)
            rrefs = a_html.find_all('b', string=re_page_rating)
            trefs = a_html.find_all('div' if playlist_name else 'span', class_=re_page_title)
            assert len(arefs) == len(rrefs) == len(trefs)
            for refpair in zip(arefs, rrefs, trefs):
                cur_id = int(re_page_entry.search(str(refpair[0].get('href'))).group(1))
                if check_id_bounds(cur_id) is False:
                    continue
                href_rel = str(refpair[0].get('href'))
                tref = str(refpair[2].text)
                my_title = tref if tref != '' else href_rel[href_rel.rfind(SLASH) + 1:] if href_rel != '' else ''
                my_rating = str(refpair[1].text)
                my_rating = '' if my_rating in ('0%', '') else my_rating[:-1]  # 0% rating doesn't mean all votes are dislikes necessarily
                v_entries.append(VideoInfo(cur_id, my_title, m_rating=my_rating))

        v_entries.reverse()
        orig_count = len(v_entries)

        if len(v_entries) > 0:
            prefilter_existing_items(v_entries)

        removed_count = orig_count - len(v_entries)

        if len(v_entries) == 0:
            if 0 < orig_count == removed_count:
                Log.fatal(f'\nAll {orig_count:d} videos already exist. Aborted.')
            else:
                Log.fatal('\nNo videos found. Aborted.')
            return

        minid, maxid = min(v_entries, key=lambda x: x.my_id).my_id, max(v_entries, key=lambda x: x.my_id).my_id
        Log.info(f'\nOk! {len(v_entries):d} ids (+{removed_count:d} filtered out), bound {minid:d} to {maxid:d}. Working...\n')

        await download(v_entries, full_download, removed_count, s)


async def run_main(args: Sequence[str]) -> None:
    await main(args)
    await sleep(0.5)


def main_sync(args: Sequence[str]) -> None:
    assert sys.version_info >= (3, 7), 'Minimum python version required is 3.7!'

    interrupted = False
    try:
        run_async(run_main(args))
    except (KeyboardInterrupt, SystemExit):
        Log.warn('Warning: catched KeyboardInterrupt/SystemExit...')
        interrupted = True
    except Exception:
        interrupted = True
    finally:
        if interrupted:
            at_interrupt()


if __name__ == '__main__':
    main_sync(sys.argv[1:])
    exit(0)

#
#
#########################################
