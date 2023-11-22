# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from typing import List, Optional, Collection, Iterable, Sequence

from bigstrings import TAG_ALIASES
from defs import TAGS_CONCAT_CHAR, LoggingFlags, PREFIX
from rex import (
    re_replace_symbols, re_wtag, re_idval, re_uscore_mult, re_not_a_letter, re_numbered_or_counted_tag, re_or_group,
    re_neg_and_group, re_tags_to_process, re_tags_to_exclude, RAW_TAGS_REPLACEMENTS,
    prepare_regex_fullmatch,
)
from logger import Log

__all__ = (
    'filtered_tags', 'get_matching_tag', 'try_parse_id_or_group', 'valid_extra_tag', 'is_filtered_out_by_extra_tags',
    'unite_separated_tags',
)


def valid_extra_tag(tag: str) -> str:
    try:
        if tag[0] == '(':
            assert is_valid_or_group(tag)
        elif tag.startswith('-('):
            assert is_valid_neg_and_group(tag)
        else:
            pass
        return tag.lower().replace(' ', '_')
    except Exception:
        Log.fatal(f'Fatal: invalid extra tag or group: \'{tag}\'!')
        raise ValueError


def is_non_wtag(tag: str) -> bool:
    return not re_wtag.fullmatch(tag)


def is_valid_neg_and_group(andgr: str) -> bool:
    return not not re_neg_and_group.fullmatch(andgr)


def is_valid_or_group(orgr: str) -> bool:
    return not not re_or_group.fullmatch(orgr)


def normalize_wtag(wtag: str) -> str:
    for c in '.[]()-+':
        wtag = wtag.replace(c, f'\\{c}')
    return wtag.replace('*', '.*').replace('?', '.')


def get_matching_tag(wtag: str, mtags: Iterable[str]) -> Optional[str]:
    if is_non_wtag(wtag):
        return wtag if wtag in mtags else None
    pat = prepare_regex_fullmatch(normalize_wtag(wtag))
    for htag in mtags:
        if pat.fullmatch(htag):
            return htag
    return None


def get_or_group_matching_tag(orgr: str, mtags: Iterable[str]) -> Optional[str]:
    for tag in orgr[1:-1].split('~'):
        mtag = get_matching_tag(tag, mtags)
        if mtag:
            return mtag
    return None


def is_neg_and_group_matches(andgr: str, mtags: Iterable[str]) -> bool:
    return all(get_matching_tag(wtag, mtags) is not None for wtag in andgr[2:-1].split(','))


def is_valid_id_or_group(orgr: str) -> bool:
    return is_valid_or_group(orgr) and all(re_idval.fullmatch(tag) for tag in orgr[1:-1].split('~'))


def try_parse_id_or_group(ex_tags: Sequence[str]) -> List[int]:
    if len(ex_tags) == 1:
        orgr = ex_tags[0]
        if is_valid_id_or_group(orgr):
            return [int(tag.replace('id=', '')) for tag in orgr[1:-1].split('~')]
    return []


def trim_undersores(base_str: str) -> str:
    return re_uscore_mult.sub('_', base_str).strip('_')


def is_filtered_out_by_extra_tags(idi: int, tags_raw: Collection[str], extra_tags: List[str], is_extra_seq: bool, subfolder: str) -> bool:
    suc = True
    sname = f'{PREFIX}{idi:d}.mp4'
    sfol = f'[{subfolder}] ' if subfolder else ''
    if len(extra_tags) > 0:
        if is_extra_seq:
            assert len(extra_tags) == 1
            id_sequence = try_parse_id_or_group(extra_tags)
            assert id_sequence
            if idi not in id_sequence:
                suc = False
                Log.trace(f'{sfol}Video {sname} isn\'t contained in id list \'{str(id_sequence)}\'. Skipped!',
                          LoggingFlags.LOGGING_EX_MISSING_TAGS)
            return not suc

        for extag in extra_tags:
            if extag[0] == '(':
                if get_or_group_matching_tag(extag, tags_raw) is None:
                    suc = False
                    Log.trace(f'{sfol}Video {sname} misses required tag matching \'{extag}\'. Skipped!',
                              LoggingFlags.LOGGING_EX_MISSING_TAGS)
            elif extag.startswith('-('):
                if is_neg_and_group_matches(extag, tags_raw):
                    suc = False
                    Log.info(f'{sfol}Video {sname} contains excluded tags combination \'{extag[1:]}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
            else:
                my_extag = extag[1:] if extag[0] == '-' else extag
                mtag = get_matching_tag(my_extag, tags_raw)
                if mtag is not None and extag[0] == '-':
                    suc = False
                    Log.info(f'{sfol}Video {sname} contains excluded tag \'{mtag}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
                elif mtag is None and extag[0] != '-':
                    suc = False
                    Log.trace(f'{sfol}Video {sname} misses required tag matching \'{my_extag}\'. Skipped!',
                              LoggingFlags.LOGGING_EX_MISSING_TAGS)
    return not suc


def unite_separated_tags(comma_separated_tags_str: str) -> str:
    words = comma_separated_tags_str
    for raw_tag_replacement_re, raw_tag_replacement_groups in RAW_TAGS_REPLACEMENTS.items():
        try:
            words = raw_tag_replacement_re.sub(raw_tag_replacement_groups, words)
        except Exception:
            Log.warn(f'Unable to apply \'{str(raw_tag_replacement_re)}\' with groups\'{raw_tag_replacement_groups}\' to string \'{words}\'!'
                     f'\nOrig was: \'{comma_separated_tags_str}\'!')
            continue
    return words


def filtered_tags(tags_list: Collection[str]) -> str:
    if len(tags_list) == 0:
        return ''

    tags_list_final = list()  # type: List[str]

    for tag in tags_list:
        tag = re_replace_symbols.sub('_', tag)
        if TAG_ALIASES.get(tag) is None and re_tags_to_process.match(tag) is None:
            continue

        alias = TAG_ALIASES.get(tag)
        if alias:
            tag = alias

        if re_tags_to_exclude.match(tag):
            continue

        tag = trim_undersores(tag)

        do_add = True
        if len(tags_list_final) > 0:
            nutag = re_not_a_letter.sub('', re_numbered_or_counted_tag.sub(r'\1', tag))
            # try and see
            # 1) if this tag can be consumed by existing tags
            # 2) if this tag can consume existing tags
            for i in reversed(range(len(tags_list_final))):
                t = re_numbered_or_counted_tag.sub(r'\1', tags_list_final[i].lower())
                nut = re_not_a_letter.sub('', t)
                if len(nut) >= len(nutag) and (nutag in nut):
                    do_add = False
                    break
            if do_add:
                for i in reversed(range(len(tags_list_final))):
                    t = re_numbered_or_counted_tag.sub(r'\1', tags_list_final[i].lower())
                    nut = re_not_a_letter.sub('', t)
                    if len(nutag) >= len(nut) and (nut in nutag):
                        del tags_list_final[i]
        if do_add:
            for i, c in enumerate(tag):  # type: int, str
                if (i == 0 or tag[i - 1] == '_') and c.isalpha():
                    tag = f'{tag[:i]}{c.upper()}{tag[i + 1:]}'
            tags_list_final.append(tag)

    return trim_undersores(TAGS_CONCAT_CHAR.join(tags_list_final))

#
#
#########################################
