# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
# Original solution by Bharel: https://stackoverflow.com/a/70664652
#

from asyncio import CancelledError, sleep
from collections.abc import Callable, Sequence
from contextlib import contextmanager, nullcontext
from platform import system
from typing import NamedTuple

from .defs import DOWNLOAD_CANCEL_KEY_SEQUENCE, DOWNLOAD_INTERRUPT_KEY_SEQUENCE, SCAN_CANCEL_KEY_SEQUENCE

__all__ = (
    'DOWNLOAD_INTERRUPT_SEQUENCE_HARD',
    'DOWNLOAD_INTERRUPT_SEQUENCE_SOFT',
    'SCAN_INTERRUPT_SEQUENCE',
    'KeySequenceAction',
    'wait_any_key_sequence',
)

if system() == 'Windows':
    import msvcrt

    set_terminal_raw = nullcontext
    input_ready = msvcrt.kbhit
    next_input = msvcrt.getwch
else:
    import functools
    import sys
    from select import select
    from termios import TCSADRAIN, tcgetattr, tcsetattr
    from tty import setraw

    @contextmanager
    def set_terminal_raw() -> None:
        fd = sys.stdin.fileno()
        old_settings = tcgetattr(fd)
        try:
            setraw(sys.stdin.fileno())
            yield
        finally:
            tcsetattr(fd, TCSADRAIN, old_settings)

    def input_ready() -> bool:
        return select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    next_input = functools.partial(sys.stdin.read, 1)


class Symbol(str):
    def __init__(self, symbol: str) -> None:
        assert len(symbol) == 1
        super().__init__()


class KeySequenceAction(NamedTuple):
    sequence: tuple[Symbol] | tuple[Symbol, Symbol] | tuple[Symbol, Symbol, Symbol]
    action: Callable[[], None]


SCAN_INTERRUPT_SEQUENCE = (Symbol(SCAN_CANCEL_KEY_SEQUENCE[0]), Symbol(SCAN_CANCEL_KEY_SEQUENCE[1]))
DOWNLOAD_INTERRUPT_SEQUENCE_SOFT = (Symbol(DOWNLOAD_CANCEL_KEY_SEQUENCE[0]), Symbol(DOWNLOAD_CANCEL_KEY_SEQUENCE[1]))
DOWNLOAD_INTERRUPT_SEQUENCE_HARD = (Symbol(DOWNLOAD_INTERRUPT_KEY_SEQUENCE[0]), Symbol(DOWNLOAD_INTERRUPT_KEY_SEQUENCE[1]))


async def wait_any_key_sequence(sequence_actions: Sequence[KeySequenceAction]) -> None:
    def clear() -> None:
        pass

    stroke_sequences: list[list[str]] = [[] for _ in sequence_actions]
    cur_idx = 0

    try:
        with set_terminal_raw():
            while True:
                await sleep(1.0)
                if not input_ready():
                    clear()
                    continue
                while any(cur_idx < len(_.sequence) for _ in sequence_actions) and input_ready():
                    ch = next_input()
                    advance = False
                    for i, ksact in enumerate(sequence_actions):
                        if cur_idx < len(ksact.sequence) and ch == ksact.sequence[cur_idx]:
                            stroke_sequences[i].append(ch)
                            advance = True
                    if advance:
                        cur_idx += 1
                    else:
                        clear()
                        while input_ready():
                            next_input()
                for idx in range(len(sequence_actions)):
                    if ''.join(stroke_sequences[idx]) == ''.join(sequence_actions[idx].sequence):
                        sequence_actions[idx].action()
                        clear()
                        break
    except CancelledError:
        pass

#
#
#########################################
