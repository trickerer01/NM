# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from base64 import b64decode


__NM_DEBUG__ = False


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
HELP_QUALITY = f'Video quality. Default is \'{DEFAULT_QUALITY}\''
HELP_ARG_PROXY = 'Proxy to use in format: a.d.d.r:port'
HELP_ARG_UVPOLICY = (
    'Unlisted videos download policy. By default these videos are ignored if you use extra +tags/-tags. Use \'always\' to override'
)
HELP_ARG_DMMODE = 'Download (file creation) mode'
HELP_ARG_EXCLUDE_TAGS = (
    'All remaining \'-args\' count as tags to exclude. Videos containing any of those tags will be skipped. Case insensitive'
)

CONNECT_RETRIES_PAGE = 5
CONNECT_RETRIES_ITEM = 10

MAX_VIDEOS_QUEUE_SIZE = 6

Log = print

TAGS_CONCAT_CHAR = ','


class DownloadResult:
    DOWNLOAD_SUCCESS = 0
    DOWNLOAD_FAIL_NOT_FOUND = 1
    DOWNLOAD_FAIL_RETRIES = 2
    DOWNLOAD_FAIL_ALREADY_EXISTS = 3

#
#
#########################################
