# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from argparse import Namespace
from base64 import b64decode
from datetime import datetime
from enum import IntEnum
from locale import getpreferredencoding
from typing import Optional
from urllib.parse import urlparse


class BaseConfig(object):
    def __init__(self) -> None:
        self.dest_base = None  # type: Optional[str]
        self.proxy = None  # type: Optional[str]
        self.min_score = None  # type: Optional[int]
        self.quality = None  # type: Optional[str]
        self.un_video_policy = None  # type: Optional[str]
        self.download_mode = None  # type: Optional[str]
        self.save_tags = None  # type: Optional[bool]
        self.extra_tags = None  # type: Optional[str]
        self.naming_flags = 0
        self.logging_flags = 0

    def read_params(self, params: Namespace) -> None:
        self.dest_base = params.path
        self.proxy = params.proxy
        self.min_score = params.minimum_score
        self.quality = params.quality
        self.un_video_policy = params.unlist_video_policy
        self.download_mode = params.download_mode
        self.save_tags = params.dump_tags
        self.extra_tags = params.extra_tags
        self.naming_flags = params.naming
        self.logging_flags = params.log_level

    @property
    def uvp(self) -> Optional[str]:
        return self.un_video_policy

    @property
    def dm(self) -> Optional[str]:
        return self.download_mode


ExtraConfig = BaseConfig()

SITE = b64decode('aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20=').decode()
# Params required: (str, int). Ex. SITE_PAGE_REQUEST_BASE % ('', 1)
SITE_PAGE_REQUEST_BASE = b64decode(
    'aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20vc2VhcmNoL3ZpZGVvcz9vPW1yJnNlYXJjaF9xdWVyeT0lcyZwYWdlPSVk').decode()
# Params required: (int). Ex. SITE_ITEM_REQUEST_BASE % (69999)
SITE_ITEM_REQUEST_BASE = b64decode('aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20vdmlkZW8vJWQv').decode()

USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:68.9) Gecko/20100101 Goanna/4.8 Firefox/68.9'
DEFAULT_HEADERS = {'User-Agent': USER_AGENT, 'Referer': SITE}
HOST = urlparse(SITE).netloc

REPLACE_SYMBOLS = r'[^\da-zA-Z.,_+%\-()\[\] ]+?'
NON_SEARCH_SYMBOLS = r'[^\da-zA-Z._\-\[\]]'

SLASH = '/'
UTF8 = 'utf-8'

QUALITIES = ['1080p', '720p', 'hi', '480p', '360p', 'SD', 'low']
QUALITY_STARTS = ['h264/', 'h264/', 'hd/', 'h264/', 'h264/', 'h264/', 'iphone/']
QUALITY_ENDS = ['_1080p', '_720p', '_hi', '_480p', '_360p', '_SD', '']

DEFAULT_QUALITY = QUALITIES[4]

# unlisted videos download policy
DOWNLOAD_POLICY_NOFILTERS = 'nofilters'
DOWNLOAD_POLICY_ALWAYS = 'always'
UVIDEO_POLICIES = [DOWNLOAD_POLICY_NOFILTERS, DOWNLOAD_POLICY_ALWAYS]
DOWNLOAD_POLICY_DEFAULT = DOWNLOAD_POLICY_NOFILTERS

# download (file creation) mode
DOWNLOAD_MODE_FULL = 'full'
DOWNLOAD_MODE_TOUCH = 'touch'
DOWNLOAD_MODES = [DOWNLOAD_MODE_FULL, DOWNLOAD_MODE_TOUCH]
DOWNLOAD_MODE_DEFAULT = DOWNLOAD_MODE_FULL

NAMING_FLAG_PREFIX = 0x01
NAMING_FLAG_SCORE = 0x02
NAMING_FLAG_TITLE = 0x04
NAMING_FLAG_TAGS = 0x08
NAMING_FLAGS_FULL = NAMING_FLAG_PREFIX | NAMING_FLAG_SCORE | NAMING_FLAG_TITLE | NAMING_FLAG_TAGS
NAMING_FLAGS = {
    'prefix': f'0x{NAMING_FLAG_PREFIX:02X}',
    'score': f'0x{NAMING_FLAG_SCORE:02X}',
    'title': f'0x{NAMING_FLAG_TITLE:02X}',
    'tags': f'0x{NAMING_FLAG_TAGS:02X}',
    'full': f'0x{NAMING_FLAGS_FULL:02X}'
}
NAMING_FLAGS_DEFAULT = NAMING_FLAGS_FULL


class LoggingFlags(IntEnum):
    LOGGING_NONE = 0x000
    LOGGING_TRACE = 0x001
    LOGGING_DEBUG = 0x002
    LOGGING_INFO = 0x004
    LOGGING_WARN = 0x008
    LOGGING_ERROR = 0x010
    LOGGING_FATAL = 0x800
    # some extra logging flags are merged into normal flags for now
    LOGGING_EX_MISSING_TAGS = LOGGING_TRACE
    LOGGING_EX_EXCLUDED_TAGS = LOGGING_INFO
    LOGGING_EX_LOW_SCORE = LOGGING_INFO
    LOGGING_ALL = LOGGING_FATAL | LOGGING_ERROR | LOGGING_WARN | LOGGING_INFO | LOGGING_DEBUG | LOGGING_TRACE

    def __str__(self) -> str:
        return f'{self._name_} (0x{self.value:03X})'


LOGGING_FLAGS = {
    'error': f'0x{LoggingFlags.LOGGING_ERROR.value:03X}',
    'warn': f'0x{LoggingFlags.LOGGING_WARN.value:03X}',
    'info': f'0x{LoggingFlags.LOGGING_INFO.value:03X}',
    'debug': f'0x{LoggingFlags.LOGGING_DEBUG.value:03X}',
    'trace': f'0x{LoggingFlags.LOGGING_TRACE.value:03X}',
}
LOGGING_FLAGS_DEFAULT = LoggingFlags.LOGGING_INFO

ACTION_STORE_TRUE = 'store_true'
ACTION_STORE_FALSE = 'store_false'

HELP_PAGES = 'Pages count to process. Required'
HELP_STOP_ID = 'If you want to download only videos above or equal to this id'
HELP_BEGIN_ID = 'If you want to download only videos above or equal to this id'
HELP_PATH = 'Download destination. Default is current folder'
HELP_SEARCH = 'If you want to only traverse pages matching some search query'
HELP_QUALITY = f'Video quality. Default is \'{DEFAULT_QUALITY}\'. If not found, anything less is used'
HELP_ARG_PROXY = 'Proxy to use. Example: http://127.0.0.1:222'
HELP_ARG_UVPOLICY = (
    'Unlisted videos download policy. By default these videos are ignored if you use extra \'tags\' / \'-tags\'. Use'
    f' \'{DOWNLOAD_POLICY_ALWAYS}\' to override'
)
HELP_ARG_DMMODE = 'Download (file creation) mode'
HELP_ARG_EXTRA_TAGS = (
    'All remaining \'args\' and \'-args\' count as tags to exclude / require.'
    ' Videos containing any of \'-tags\', or not containing all of \'tags\' will be skipped.'
)
HELP_ARG_DWN_SCENARIO = (
    'Download scenario. This allows to scan for tags and sort videos accordingly in a single pass.'
    ' Useful when you have several queries you need to process for same id range.'
    ' Format:'
    ' "{SUBDIR1}: tag1 tag2; {SUBDIR2}: tag3 tag4 -tag1 -tag2"'
    ' You can also use following arguments in each subquery: -quality, -minscore, -uvp.'
    ' Example:'
    ' \'python ids.py -path ... -start ... -end ... --download-scenario'
    ' "1g: 1girl -1monster -quality 480p; 2g: 2girls -1girl -1monster -quality 720p -minscore 150 -uvp always"\''
)
HELP_ARG_MINSCORE = (
    'Score filter for videos (likes minus dislikes).'
    ' Videos having score below this value will be skipped, unless score extraction fails - in that case video always gets a pass'
)
HELP_ARG_CMDFILE = (
    'Full path to file containing cmdline arguments. One word per line. Useful when cmdline length exceeds maximum for your OS.'
    ' Windows: ~32000, MinGW: ~4000 to ~32000, Linux: ~127000+'
)
HELP_ARG_NAMING = (
    f'File naming flags: {str(NAMING_FLAGS)}.'
    f' You can combine them via names \'prefix|score|title\', otherwise it has to be an int or a hex number.'
    f' Default is \'full\''
)
HELP_ARG_LOGGING = (
    f'Logging level: {str(list(LOGGING_FLAGS.keys()))}. All messages equal or above this level will be logged. Default is \'info\''
)

CONNECT_RETRIES_PAGE = 50
CONNECT_RETRIES_ITEM = 50
CONNECT_REQUEST_DELAY = 1.0

MAX_VIDEOS_QUEUE_SIZE = 6

TAGS_CONCAT_CHAR = ','
start_time = datetime.now()


class Log:
    @staticmethod
    def log(text: str, flags: LoggingFlags) -> None:
        # if flags & LoggingFlags.LOGGING_FATAL == 0 and ExtraConfig.logging_flags & flags != flags:
        if flags < ExtraConfig.logging_flags:
            return

        try:
            print(text)
        except UnicodeError:
            # print(f'message was: {bytearray(map(ord, text))}')
            try:
                print(text.encode(UTF8).decode())
            except Exception:
                try:
                    print(text.encode(UTF8).decode(getpreferredencoding()))
                except Exception:
                    print('<Message was not logged due to UnicodeError>')
            finally:
                print('Previous message caused UnicodeError...')

    @staticmethod
    def fatal(text: str) -> None:
        return Log.log(text, LoggingFlags.LOGGING_FATAL)

    @staticmethod
    def error(text: str, extra_flags=LoggingFlags.LOGGING_NONE) -> None:
        return Log.log(text, LoggingFlags.LOGGING_ERROR | extra_flags)

    @staticmethod
    def warn(text: str, extra_flags=LoggingFlags.LOGGING_NONE) -> None:
        return Log.log(text, LoggingFlags.LOGGING_WARN | extra_flags)

    @staticmethod
    def info(text: str, extra_flags=LoggingFlags.LOGGING_NONE) -> None:
        return Log.log(text, LoggingFlags.LOGGING_INFO | extra_flags)

    @staticmethod
    def debug(text: str, extra_flags=LoggingFlags.LOGGING_NONE) -> None:
        return Log.log(text, LoggingFlags.LOGGING_DEBUG | extra_flags)

    @staticmethod
    def trace(text: str, extra_flags=LoggingFlags.LOGGING_NONE) -> None:
        return Log.log(text, LoggingFlags.LOGGING_TRACE | extra_flags)


def prefixp() -> str:
    return 'nm_'


def get_elapsed_time_s() -> str:
    mm, ss = divmod((datetime.now() - start_time).seconds, 60)
    hh, mm = divmod(mm, 60)
    return f'{hh:02d}:{mm:02d}:{ss:02d}'


def normalize_path(basepath: str, append_slash: bool = True) -> str:
    normalized_path = basepath.replace('\\', SLASH)
    if append_slash and len(normalized_path) != 0 and normalized_path[-1] != SLASH:
        normalized_path += SLASH
    return normalized_path


def has_naming_flag(flag: int) -> bool:
    return not not ExtraConfig.naming_flags & flag


class DownloadResult:
    DOWNLOAD_SUCCESS = 0
    DOWNLOAD_FAIL_NOT_FOUND = 1
    DOWNLOAD_FAIL_RETRIES = 2
    DOWNLOAD_FAIL_ALREADY_EXISTS = 3

#
#
#########################################
