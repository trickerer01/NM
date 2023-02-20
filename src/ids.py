# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import sys
from asyncio import run as run_async, sleep

from cmdargs import prepare_arglist_ids, read_cmdfile, is_parsed_cmdfile
from defs import Log, DOWNLOAD_POLICY_DEFAULT, ExtraConfig
from download import DownloadWorker, at_interrupt
from path_util import prefilter_existing_items
from scenario import DownloadScenario
from tagger import try_parse_id_or_group

__all__ = ()


async def main() -> None:
    try:
        arglist = prepare_arglist_ids(sys.argv[1:])
        while is_parsed_cmdfile(arglist):
            arglist = prepare_arglist_ids(read_cmdfile(arglist.path))
    except Exception:
        Log.fatal(f'\nUnable to parse cmdline. Exiting.\n{sys.exc_info()[0]}: {sys.exc_info()[1]}')
        return

    try:
        ExtraConfig.read_params(arglist)
        start_id = arglist.start  # type: int
        end_id = arglist.end  # type: int
        ds = arglist.download_scenario  # type: DownloadScenario

        if arglist.use_id_sequence is True:
            id_sequence = try_parse_id_or_group(ExtraConfig.extra_tags)
            if id_sequence is None:
                Log.fatal(f'\nInvalid ID \'or\' group \'{ExtraConfig.extra_tags[0] if len(ExtraConfig.extra_tags) > 0 else ""}\'!')
                raise ValueError
        else:
            id_sequence = None
            if start_id > end_id:
                Log.fatal(f'\nError: start ({start_id:d}) > end ({end_id:d})')
                raise ValueError

        delay_for_message = False
        if ds is not None:
            if ExtraConfig.uvp != DOWNLOAD_POLICY_DEFAULT:
                Log.info('Info: running download script, outer unlisted policy will be ignored')
                ExtraConfig.uvp = DOWNLOAD_POLICY_DEFAULT
                delay_for_message = True
            if len(ExtraConfig.extra_tags) > 0:
                Log.info(f'Info: running download script: outer extra tags: {str(ExtraConfig.extra_tags)}')
                delay_for_message = True

        if delay_for_message is True:
            await sleep(3.0)
    except Exception:
        Log.fatal('\nError reading parsed arglist!')
        return

    if id_sequence is None:
        id_sequence = list(range(start_id, end_id + 1))
    else:
        ExtraConfig.extra_tags.clear()

    prefilter_existing_items(id_sequence)

    await DownloadWorker(((idi, '', 'unk', ds) for idi in id_sequence)).run()


async def run_main() -> None:
    await main()
    await sleep(0.5)


if __name__ == '__main__':
    assert sys.version_info >= (3, 7), 'Minimum python version required is 3.7!'
    try:
        run_async(run_main())
    except (KeyboardInterrupt, SystemExit):
        Log.warn(f'Warning: catched KeyboardInterrupt/SystemExit...')
        at_interrupt()
    exit(0)

#
#
#########################################
