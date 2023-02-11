# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import sleep, get_running_loop, Lock as AsyncLock
from random import uniform as frand
from typing import Optional, List

from bs4 import BeautifulSoup
from aiohttp import ClientSession, ClientResponse

from defs import CONNECT_RETRIES_PAGE, Log, DEFAULT_HEADERS, CONNECT_REQUEST_DELAY, ExtraConfig

__all__ = ('wrap_request', 'fetch_html')


class RequestQueue:
    _queue = []  # type: List[str]
    _ready = True
    _lock = AsyncLock()

    @staticmethod
    async def _reset() -> None:
        await sleep(frand(CONNECT_REQUEST_DELAY - 0.25, CONNECT_REQUEST_DELAY + 0.25))
        RequestQueue._ready = True

    @staticmethod
    async def until_ready(url: str) -> None:
        RequestQueue._queue.append(url)
        while RequestQueue._ready is False or RequestQueue._queue[0] != url:
            await sleep(0.1)
        async with RequestQueue._lock:
            del RequestQueue._queue[0]
            RequestQueue._ready = False
            get_running_loop().create_task(RequestQueue._reset())


async def wrap_request(s: ClientSession, method: str, url: str, **kwargs) -> ClientResponse:
    await RequestQueue.until_ready(url)
    Log.debug(f'wrap_request: {url}')
    s.headers.update(DEFAULT_HEADERS.copy())
    kwargs.update(proxy=ExtraConfig.proxy)
    r = await s.request(method, url, **kwargs)
    return r


async def fetch_html(url: str, *, tries: int = None, session: ClientSession) -> Optional[BeautifulSoup]:
    # very basic, minimum validation
    tries = tries or CONNECT_RETRIES_PAGE

    r = None
    retries = 0
    while retries < tries:
        try:
            async with await wrap_request(
                    session, 'GET', url, timeout=5) as r:
                if r.status != 404:
                    r.raise_for_status()
                content = await r.read()
                return BeautifulSoup(content, 'html.parser')
        except Exception:
            if r is not None and str(r.url).find('404.') != -1:
                Log.error('ERROR: 404')
                assert False
            elif r is not None:
                Log.error(f'fetch_html exception: status {r.status:d}')
            retries += 1
            if retries < tries:
                await sleep(frand(1.0, 7.0))
            continue

    if retries >= tries:
        errmsg = f'Unable to connect. Aborting {url}'
        Log.error(errmsg)
    elif r is None:
        Log.error('ERROR: Failed to receive any data')

    return None

#
#
#########################################
