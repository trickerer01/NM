# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import sleep

from .config import Config
from .defs import (
    SITE_ITEM_REQUEST_FAVOURITES_PAGE,
    SITE_ITEM_REQUEST_PLAYLIST_PAGE,
    SITE_ITEM_REQUEST_SEARCH_PAGE,
    SITE_ITEM_REQUEST_UPLOADER_PAGE,
    NamingFlags,
)
from .download import download
from .fetch_html import create_session, fetch_html
from .iinfo import VideoInfo
from .logger import Log
from .path_util import prefilter_existing_items
from .rex import re_page_entry
from .util import get_time_seconds, has_naming_flag
from .validators import find_and_resolve_config_conflicts
from .version import APP_NAME

__all__ = ('process_pages',)


async def process_pages() -> int:
    full_download = True
    video_ref_class1 = 'col-6 col-sm-6 col-md-4 col-lg-3 col-xl-2dot4 i-container'
    video_ref_class2 = 'col-6 col-sm-6 col-md-4 col-lg-4 col-xl-3'

    if find_and_resolve_config_conflicts() is True:
        await sleep(3.0)

    def check_id_bounds(video_id: int) -> int:
        if video_id > Config.end_id:
            Log.trace(f'skipping {video_id:d} > {Config.end_id:d}')
            return 1
        if video_id < Config.start_id:
            Log.trace(f'skipping {video_id:d} < {Config.start_id:d}')
            return -1
        return 0

    v_entries: list[VideoInfo] = []
    maxpage = Config.end if Config.start == Config.end else 0

    pi = Config.start
    async with create_session():
        while pi <= Config.end:
            if pi > maxpage > 0:
                Log.info('reached parsed max page, page scan completed')
                break

            page_addr = (
                (SITE_ITEM_REQUEST_PLAYLIST_PAGE % (Config.playlist_name, pi)) if Config.playlist_name else
                (SITE_ITEM_REQUEST_FAVOURITES_PAGE % (Config.favourites, pi)) if Config.favourites else
                (SITE_ITEM_REQUEST_UPLOADER_PAGE % (Config.uploader, pi)) if Config.uploader else
                (SITE_ITEM_REQUEST_SEARCH_PAGE % (Config.search, pi))
            )
            a_html = await fetch_html(page_addr, cookies={'show_category_21': '1', 'show_category_22': '1'})
            if not a_html:
                Log.error(f'Error: cannot get html for page {pi:d}')
                continue

            if not len(a_html):
                Log.error(f'Error: got empty HTML for page {pi}! Retrying...')
                continue

            pi += 1

            if maxpage == 0 or pi - 1 == maxpage:
                old_maxpage = maxpage
                if Config.playlist_name and any('Error' in (d.string, d.text) for d in a_html.find_all('legend')):
                    Log.fatal(f'\nFatal: playlist is not found for user \'{Config.playlist_name}\'!')
                    return -1
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
                mirefs = a_html.find_all('div', class_=video_ref_class1)
                mirefs = mirefs or a_html.find_all('div', class_=video_ref_class2)
                mirefs = [_.find('a') for _ in mirefs]
                max_id = max(int(re_page_entry.search(_.get('href')).group(1)) for _ in mirefs)
                Log.fatal(f'{APP_NAME}: {max_id:d}')
                return 0

            Log.info(f'page {pi - 1:d}...{" (this is the last page!)" if (0 < maxpage == pi - 1) else ""}')

            vrefs = a_html.find_all('div', class_=video_ref_class1)
            vrefs = vrefs or a_html.find_all('div', class_=video_ref_class2)
            lower_count = 0
            orig_count = len(vrefs)
            for vref in vrefs:
                aref = vref.find_all('a')[-1]
                rref = vref.find('span', class_='content-rating')
                tref = aref.find('span')
                dref = vref.find('div', class_='duration')
                cur_id = int(re_page_entry.search(aref.get('href')).group(1))
                if bound_res := check_id_bounds(cur_id):
                    if bound_res < 0:
                        lower_count += 1
                    continue
                my_title = str(tref.text)
                my_utitle = str(aref['href'][aref['href'].rfind('/') + 1:])
                my_rating = str(rref.find('span').text) if rref else ''
                my_rating = '' if my_rating in ('0%', '') else my_rating[:-1]  # 0% rating doesn't mean all votes are dislikes necessarily
                my_duration = get_time_seconds(str(dref.get_text(strip=True).replace('HD', '')))
                use_utitle = has_naming_flag(NamingFlags.USE_URL_TITLE)
                v_entries.append(VideoInfo(cur_id, my_utitle if use_utitle else my_title, m_rating=my_rating, m_duration=my_duration))

            if pi - 1 > Config.start and 0 < lower_count == orig_count and not Config.scan_all_pages:
                if not (0 < maxpage <= pi - 1):
                    Log.info(f'Page {pi - 1:d} has all post ids below lower bound. Pages scan stopped!')
                break

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
            return -1

        await download(v_entries, full_download, removed_count)

    return 0

#
#
#########################################
