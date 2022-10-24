# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import run as run_async, sleep, as_completed
from sys import argv

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist_ids
from defs import Log, MAX_VIDEOS_QUEUE_SIZE, DEFAULT_HEADERS
from download import download_id, failed_items
from fetch_html import set_proxy


async def main() -> None:
    try:
        arglist = prepare_arglist_ids(argv[1:])
    except Exception:
        Log('\nUnable to parse cmdline. Exiting...')
        return

    try:
        dest_base = arglist.path
        start_id = arglist.start
        end_id = arglist.end
        quality = arglist.max_quality
        extra_tags = arglist.extra_tags
        set_proxy(arglist.proxy if hasattr(arglist, 'proxy') else None)

        if start_id > end_id:
            Log(f'\nError: start ({start_id:d}) > end ({end_id:d})')
            raise ValueError
    except Exception:
        Log('\nError reading parsed arglist!')
        return

    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        s.headers.update(DEFAULT_HEADERS.copy())
        for cv in as_completed([download_id(idi, '', 'unk', dest_base, quality, extra_tags, s) for idi in range(start_id, end_id + 1)]):
            await cv

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
    # Log('Searching by ID is disabled, reason: Buggy, videos are not properly sorted by id, meking binary search mostly useless')
    exit(0)

#
#
#########################################
