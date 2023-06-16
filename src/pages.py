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

from cmdargs import prepare_arglist_pages, read_cmdfile, is_parsed_cmdfile
from defs import (
    VideoInfo, Log, ExtraConfig, SITE_ITEM_REQUEST_PAGE, SLASH,
    HelpPrintExitException,
)
from download import download, at_interrupt
from path_util import prefilter_existing_items, scan_dest_folder
from fetch_html import make_session, fetch_html
from validators import find_and_resolve_config_conflicts

__all__ = ()


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

        full_download = True
        re_page_entry = re_compile(r'^/video/(\d+)/[^/]+?$')

        if find_and_resolve_config_conflicts() is True:
            await sleep(3.0)
    except Exception:
        Log.fatal('\nError reading parsed arglist!')
        return

    v_entries = list()
    maxpage = 0

    pi = start_page
    async with await make_session() as s:
        while pi < start_page + pages_count:
            if pi > maxpage > 0:
                Log.info('reached parsed max page, page scan completed')
                break
            Log.info(f'page {pi:d}...{" (this is the last page!)" if (0 < maxpage == pi) else ""}')

            a_html = await fetch_html(SITE_ITEM_REQUEST_PAGE % (search_str, pi), session=s)
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

            arefs = a_html.find_all('a', href=re_page_entry)
            rrefs = a_html.find_all('b', string=re_compile(r'^(?:\d{1,3}%|-)$'))
            trefs = a_html.find_all('span', class_='video-title title-truncate m-t-5')
            assert len(arefs) == len(rrefs) == len(trefs)
            for refpair in zip(arefs, rrefs, trefs):
                cur_id = int(re_page_entry.search(str(refpair[0].get('href'))).group(1))
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
                my_rating = '' if my_rating in ['0%', ''] else my_rating[:-1]  # 0% rating doesn't mean all votes are dislikes necessarily
                v_entries.append(VideoInfo(cur_id, my_title, m_rating=my_rating))

        v_entries.reverse()
        orig_count = len(v_entries)

        if len(v_entries) > 0:
            scan_dest_folder()
            removed_ids = prefilter_existing_items([v.my_id for v in v_entries])
            for i in reversed(range(len(v_entries))):
                if v_entries[i].my_id in removed_ids:
                    del v_entries[i]

        removed_count = orig_count - len(v_entries)

        if len(v_entries) == 0:
            if 0 < orig_count == removed_count:
                Log.fatal(f'\nAll {orig_count:d} videos already exist. Aborted.')
            else:
                Log.fatal('\nNo videos found. Aborted.')
            return

        minid, maxid = min(v_entries, key=lambda x: x.my_id).my_id, max(v_entries, key=lambda x: x.my_id).my_id
        Log.info(f'\nOk! {len(v_entries):d} videos found (+{removed_count:d} filtered out), bound {minid:d} to {maxid:d}. Working...\n')

        await download(v_entries, full_download, removed_count, s)


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
    except Exception:
        at_interrupt()
    exit(0)

#
#
#########################################
