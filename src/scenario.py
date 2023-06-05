# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from argparse import ArgumentParser, ZERO_OR_MORE, ArgumentError
from typing import List, Optional

from defs import (
    Log, DEFAULT_QUALITY, HELP_QUALITY, QUALITIES, HELP_ARG_UVPOLICY, UVIDEO_POLICIES, HELP_ARG_EXTRA_TAGS, DOWNLOAD_POLICY_DEFAULT,
    DOWNLOAD_POLICY_ALWAYS, HELP_ARG_MINRATING, HELP_ARG_MINSCORE, ACTION_STORE_TRUE, HELP_ARG_IDSEQUENCE,
)
from tagger import valid_extra_tag, try_parse_id_or_group
from validators import valid_int, valid_rating

__all__ = ('DownloadScenario')

UVP_DEFAULT = DOWNLOAD_POLICY_DEFAULT
"""'nofilters'"""
UVP_ALWAYS = DOWNLOAD_POLICY_ALWAYS
"""'always'"""


class SubQueryParams(object):
    def __init__(self, subfolder: str, extra_tags: List[str], quality: str, minscore: int, minrating: int,
                 uvp: str, use_id_sequence: bool) -> None:
        self.subfolder = subfolder or ''  # type: str
        self.extra_tags = extra_tags or []  # type: List[str]
        self.quality = quality or ''  # type: str
        self.minrating = minrating or 0  # type: int
        self.minscore = minscore  # type: Optional[int]
        self.unlist_video_policy = uvp or ''  # type: str
        self.use_id_sequence = use_id_sequence or False  # type: bool

    @property
    def uvp(self) -> str:
        return self.unlist_video_policy

    def __repr__(self) -> str:
        return (
            f'sub: \'{self.subfolder}\', '
            f'quality: \'{self.quality}\', '
            f'minrating: \'{self.minrating:d}\', '
            f'minscore: \'{str(self.minscore)}\', '
            f'uvp: \'{self.uvp}\', '
            f'use_id_sequence: \'{self.use_id_sequence}\', '
            f'tags: \'{str(self.extra_tags)}\''
        )


class DownloadScenario(object):
    def __init__(self, fmt_str: str) -> None:
        self.queries = []  # type: List[SubQueryParams]
        if fmt_str is None:
            return

        parser = ArgumentParser(add_help=False)
        parser.add_argument('-seq', '--use-id-sequence', action=ACTION_STORE_TRUE, help=HELP_ARG_IDSEQUENCE)
        parser.add_argument('-quality', default=DEFAULT_QUALITY, help=HELP_QUALITY, choices=QUALITIES)
        parser.add_argument('-minrating', '--minimum-rating', metavar='#0-100', default=0, help=HELP_ARG_MINRATING, type=valid_rating)
        parser.add_argument('-minscore', '--minimum-score', metavar='#score', default=None, help=HELP_ARG_MINSCORE, type=valid_int)
        parser.add_argument('-uvp', '--unli-video-policy', default=UVP_DEFAULT, help=HELP_ARG_UVPOLICY, choices=UVIDEO_POLICIES)
        parser.add_argument(dest='extra_tags', nargs=ZERO_OR_MORE, help=HELP_ARG_EXTRA_TAGS, type=valid_extra_tag)

        for query_raw in fmt_str.split('; '):
            error_to_print = ''
            try:
                subfolder, args = query_raw.split(': ')
                parsed, unks = parser.parse_known_args(args.split())
                for tag in unks:
                    try:
                        assert valid_extra_tag(tag)
                        if parsed.use_id_sequence is True:
                            assert len(unks) == 1
                            assert try_parse_id_or_group([tag]) is not None
                    except Exception:
                        error_to_print = f'\nInvalid extra tag: \'{tag}\'\n'
                        raise
                parsed.extra_tags += [tag.lower().replace(' ', '_') for tag in unks]
                if parsed.unli_video_policy == UVP_ALWAYS and self.has_subquery(unlist_video_policy=UVP_ALWAYS):
                    error_to_print = f'Scenario can only have one subquery with unlisted video policy \'{UVP_ALWAYS}\'!'
                    raise ValueError
                self.add_subquery(SubQueryParams(
                    subfolder, parsed.extra_tags, parsed.quality, parsed.minimum_score, parsed.minimum_rating,
                    parsed.unli_video_policy, parsed.use_id_sequence
                ))
            except (ArgumentError, TypeError, Exception):
                if error_to_print != '':
                    Log.error(error_to_print)
                raise

        assert len(self) > 0

    def __len__(self) -> int:
        return len(self.queries)

    def add_subquery(self, subquery: SubQueryParams) -> None:
        self.queries.append(subquery)

    def has_subquery(self, **kwargs) -> bool:
        for sq in self.queries:
            all_matched = True
            for k, v in kwargs.items():
                if not (k in sq.__dict__.keys() and sq.__getattribute__(k) == v):
                    all_matched = False
                    break
            if all_matched is True:
                return True
        return False

    def get_uvp_always_subquery_idx(self) -> int:
        for idx, sq in enumerate(self.queries):
            if sq.uvp == UVP_ALWAYS:
                return idx
        return -1

#
#
#########################################
