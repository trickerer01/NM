# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from base64 import b64decode
from datetime import datetime


__NM_DEBUG__ = False


class BaseConfig(object):
    def __init__(self):
        self.verbose = False


ExtraConfig = BaseConfig()

SITE_BASE = b64decode('aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20=').decode()
# Params required: (str, int). Ex. SITE_PAGE_REQUEST_BASE % ('', 1)
SITE_PAGE_REQUEST_BASE = b64decode(
    'aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20vc2VhcmNoL3ZpZGVvcz9vPW1yJnNlYXJjaF9xdWVyeT0lcyZwYWdlPSVk').decode()
# Params required: (int). Ex. SITE_ITEM_REQUEST_BASE % (69999)
SITE_ITEM_REQUEST_BASE = b64decode('aHR0cHM6Ly93d3cubmF1Z2h0eW1hY2hpbmltYS5jb20vdmlkZW8vJWQv').decode()

USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:68.9) Gecko/20100101 Goanna/4.8 Firefox/68.9'
DEFAULT_HEADERS = {'User-Agent': USER_AGENT}

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
    ' Videos containing any of \'-tags\', or not containing all of \'tags\' will be skipped'
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
    ' Videos having score below this value will be skipped, unless score extraction fails - in that case video always get a pass'
)

CONNECT_RETRIES_PAGE = 5
CONNECT_RETRIES_ITEM = 10

MAX_VIDEOS_QUEUE_SIZE = 6

Log = print

TAGS_CONCAT_CHAR = ','
start_time = datetime.now()


def get_elapsed_time_s() -> str:
    mm, ss = divmod((datetime.now() - start_time).seconds, 60)
    hh, mm = divmod(mm, 60)
    return f'{hh:02d}:{mm:02d}:{ss:02d}'


def normalize_path(basepath: str, append_slash: bool = True) -> str:
    normalized_path = basepath.replace('\\', SLASH)
    if append_slash and len(normalized_path) != 0 and normalized_path[-1] != SLASH:
        normalized_path += SLASH
    return normalized_path


class DownloadResult:
    DOWNLOAD_SUCCESS = 0
    DOWNLOAD_FAIL_NOT_FOUND = 1
    DOWNLOAD_FAIL_RETRIES = 2
    DOWNLOAD_FAIL_ALREADY_EXISTS = 3

#
#
#########################################
