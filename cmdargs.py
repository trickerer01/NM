# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import os.path as path
from argparse import ArgumentParser, Namespace, ArgumentError
from re import match as re_match
from typing import Optional, List

from defs import SLASH_CHAR, Log, NON_SEARCH_SYMBOLS, HELP_PATH, HELP_PAGES, HELP_STOP_ID, HELP_SEARCH, QUALITIES, HELP_QUALITY


parser = None  # type: Optional[ArgumentParser]


def unquote(string: str) -> str:
    try:
        while True:
            found = False
            if len(string) > 1 and string[0] in ['\'', '"']:
                string = string[1:]
                found = True
            if len(string) > 1 and string[-1] in ['\'', '"']:
                string = string[:-1]
                found = True
            if not found:
                break
        return string
    except Exception:
        raise ValueError


def valid_positive_nonzero_int(val: str) -> int:
    try:
        val = int(val)
        assert(val > 0)
    except Exception:
        raise ArgumentError

    return val


def valid_path(pathstr: str) -> str:
    try:
        newpath = path.abspath(unquote(pathstr)).replace('\\', SLASH_CHAR)
        if not path.exists(newpath[:(newpath.find(SLASH_CHAR) + 1)]):
            raise ValueError
        if newpath[-1] != SLASH_CHAR:
            newpath += SLASH_CHAR
    except Exception:
        raise ArgumentError

    return newpath


def valid_search_string(search_str: str) -> str:
    try:
        if len(search_str) > 0 and re_match(r'^.*' + NON_SEARCH_SYMBOLS + '.*$', search_str):
            raise ValueError
    except Exception:
        raise ArgumentError

    return search_str


def validate_parsed(args) -> Namespace:
    global parser
    try:
        parsed, unk = parser.parse_known_args(args)
        if len(unk) > 0:
            Log('\ninvalid arguments found:', str(unk) + '\n')
            raise ArgumentError
        # Log('parsed:', parsed)
    except (ArgumentError, TypeError, Exception):
        # Log('\n', e)
        parser.print_help()
        raise

    return parsed


def prepare_arglist(args: List[str]) -> Namespace:
    global parser

    parser = ArgumentParser()

    parser.add_argument('-start', metavar='#number', default=1, help='Start page number. Default is \'1\'', type=valid_positive_nonzero_int)
    parser.add_argument('-pages', metavar='#number', required=True, help=HELP_PAGES, type=valid_positive_nonzero_int)
    parser.add_argument('-stop_id', metavar='#number', default=1, help=HELP_STOP_ID, type=valid_positive_nonzero_int)
    parser.add_argument('-search', metavar='#string', default='', help=HELP_SEARCH, type=valid_search_string)
    parser.add_argument('-path', default=path.abspath(path.curdir), help=HELP_PATH, type=valid_path)
    parser.add_argument('-max_quality', default=QUALITIES[3], help=HELP_QUALITY, choices=QUALITIES)

    try:
        return validate_parsed(args)
    except (ArgumentError, TypeError, Exception):
        raise

#
#
#########################################
