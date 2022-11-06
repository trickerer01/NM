# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import run as run_async, sleep, as_completed, get_running_loop
from sys import argv

from aiohttp import ClientSession, TCPConnector

from cmdargs import prepare_arglist_ids
from defs import Log, MAX_VIDEOS_QUEUE_SIZE, DEFAULT_HEADERS, DOWNLOAD_MODE_FULL
from download import download_id, after_download, report_total_queue_size_callback, register_id_sequence
from fetch_html import set_proxy
from tagger import try_parse_id_or_group, init_tags_file, dump_item_tags


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
        up = arglist.unli_video_policy
        dm = arglist.download_mode
        st = arglist.dump_tags
        ex_tags = arglist.extra_tags
        set_proxy(arglist.proxy if hasattr(arglist, 'proxy') else None)

        if arglist.use_id_sequence:
            id_sequence = try_parse_id_or_group(ex_tags)
            if id_sequence is None:
                Log(f'\nInvalid ID \'or\' group \'{ex_tags[0] if len(ex_tags) > 0 else ""}\'!')
                raise ValueError
        else:
            id_sequence = None
            if start_id > end_id:
                Log(f'\nError: start ({start_id:d}) > end ({end_id:d})')
                raise ValueError
    except Exception:
        Log('\nError reading parsed arglist!')
        return

    if id_sequence is None:
        id_sequence = list(range(start_id, end_id + 1))
    else:
        ex_tags = []

    if st:
        init_tags_file(f'{dest_base}nm_!tags_{start_id:d}-{end_id:d}.txt')
    register_id_sequence(id_sequence)
    reporter = get_running_loop().create_task(report_total_queue_size_callback(3.0 if dm == DOWNLOAD_MODE_FULL else 1.0))
    async with ClientSession(connector=TCPConnector(limit=MAX_VIDEOS_QUEUE_SIZE), read_bufsize=2**20) as s:
        s.headers.update(DEFAULT_HEADERS.copy())
        for cv in as_completed([download_id(idi, '', 'unk', dest_base, quality, ex_tags, up, dm, st, s) for idi in id_sequence]):
            await cv
    await reporter

    if st:
        dump_item_tags()

    await after_download()


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
