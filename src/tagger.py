# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from typing import List, Optional, Collection, Iterable, MutableSequence, Tuple, Union, Literal

from bigstrings import TAG_ALIASES
from config import Config
from defs import LoggingFlags, TAGS_CONCAT_CHAR
from logger import Log
from rex import (
    re_replace_symbols, re_wtag, re_idval, re_uscore_mult, re_not_a_letter, re_numbered_or_counted_tag, re_or_group,
    re_neg_and_group, re_tags_to_process, re_tags_to_exclude, RAW_TAGS_REPLACEMENTS,
    prepare_regex_fullmatch,
)
from vinfo import VideoInfo

__all__ = (
    'filtered_tags', 'get_matching_tag', 'extract_id_or_group', 'valid_extra_tag', 'is_filtered_out_by_extra_tags',
    'valid_playlist_name', 'unite_separated_tags',
)


def valid_playlist_name(plist: str) -> Tuple[int, str]:
    try:
        plist_name, plist_numb = plist, 0
        return (plist_numb, plist_name)
    except Exception:
        raise ValueError


def valid_extra_tag(tag: str, log=True) -> str:
    try:
        pass
        if tag.startswith('('):
            assert is_valid_or_group(tag)
            pass
        elif tag.startswith('-('):
            assert is_valid_neg_and_group(tag)
            pass
        else:
            pass
        pass
        return tag.lower().replace(' ', '_')
    except Exception:
        if log:
            Log.fatal(f'Fatal: invalid extra tag or group: \'{tag}\'!')
        raise ValueError


def is_wtag(tag: str) -> bool:
    return not not re_wtag.fullmatch(tag)


def is_valid_neg_and_group(andgr: str) -> bool:
    return not not re_neg_and_group.fullmatch(andgr)


def is_valid_or_group(orgr: str) -> bool:
    return not not re_or_group.fullmatch(orgr)


def normalize_wtag(wtag: str) -> str:
    for c in '.()-+':
        wtag = wtag.replace(c, f'\\{c}')
    return wtag.replace('*', '.*').replace('?', '.')


def get_matching_tag(wtag: str, mtags: Iterable[str], *, force_regex=False) -> Optional[str]:
    if not is_wtag(wtag) and not force_regex:
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


def get_neg_and_group_matches(andgr: str, mtags: Iterable[str]) -> List[str]:
    matched_tags = list()
    for wtag in andgr[2:-1].split(','):
        mtag = get_matching_tag(wtag, mtags, force_regex=True)
        if not mtag:
            return []
        matched_tags.append(mtag)
    return matched_tags


def is_valid_id_or_group(orgr: str) -> bool:
    return is_valid_or_group(orgr) and all(re_idval.fullmatch(tag) for tag in orgr[1:-1].split('~'))


def extract_id_or_group(ex_tags: MutableSequence[str]) -> List[int]:
    """May alter the input container!"""
    for i in range(len(ex_tags)):
        orgr = ex_tags[i]
        if is_valid_id_or_group(orgr):
            del ex_tags[i]
            return [int(tag.replace('id=', '')) for tag in orgr[1:-1].split('~')]
    return []


def convert_extra_tag_for_text_matching(ex_tag: str) -> str:
    if ex_tag.startswith('-('):
        wtags, tagtype = ex_tag[2:-1].split(','), 1
    elif ex_tag.startswith('('):
        wtags, tagtype = ex_tag[1:-1].split('~'), 2
    elif ex_tag.startswith('-'):
        wtags, tagtype = [ex_tag[1:]], 3
    else:
        wtags, tagtype = [ex_tag], 4

    # language=PythonRegExp
    norm_str = r'[ ()\[\]_\'"]'
    for i, wtag in enumerate(wtags):
        wtag_begin = '' if wtag.startswith("*") else '*' if wtag.startswith(tuple(norm_str[1:-1].split())) else f'*{norm_str}'
        wtag_end = '' if wtag.endswith("*") else '*' if wtag.endswith(tuple(norm_str[1:-1].split())) else f'{norm_str}*'
        wtags[i] = f'{wtag_begin}{wtag.replace("_", " ")}{wtag_end}'

    conv_tag = (
        f'-({",".join(wtags)})' if tagtype == 1 else f'({"~".join(wtags)})' if tagtype == 2 else
        f'-{"".join(wtags)}' if tagtype == 3 else f'{"".join(wtags)}'
    )
    return conv_tag


def match_text(ex_tag: str, text: str, group_type: Literal['or', 'and'] = '') -> Union[None, str, List[str]]:
    converted_tag = convert_extra_tag_for_text_matching(ex_tag)
    text = text.replace('\n', ' ').strip().lower()
    if group_type == 'or':
        return get_or_group_matching_tag(converted_tag, [text])
    elif group_type == 'and':
        return get_neg_and_group_matches(converted_tag, [text])
    else:
        return get_matching_tag(converted_tag, [text])


def trim_undersores(base_str: str) -> str:
    return re_uscore_mult.sub('_', base_str).strip('_')


def is_filtered_out_by_extra_tags(vi: VideoInfo, tags_raw: List[str], extra_tags: List[str],
                                  id_seq: List[int], subfolder: str, id_seq_ex: List[int] = None) -> bool:
    suc = True
    sname = vi.sname
    sfol = f'[{subfolder}] ' if subfolder else ''
    if id_seq and vi.id not in id_seq and not (id_seq_ex and vi.id in id_seq_ex):
        suc = False
        Log.trace(f'{sfol}Video {sname} isn\'t contained in id list \'{str(id_seq)}\'. Skipped!',
                  LoggingFlags.EX_MISSING_TAGS)

    for extag in extra_tags:
        if extag.startswith('('):
            or_match_base = get_or_group_matching_tag(extag, tags_raw)
            or_match_titl = match_text(extag, vi.title, 'or') if Config.check_title_pos and vi.title else None
            or_match_desc = match_text(extag, vi.description, 'or') if Config.check_description_pos and vi.description else None
            if or_match_titl:
                Log.trace(f'{sfol}Video {sname} has TITL POS match: {str(or_match_titl)}')
            if or_match_desc:
                Log.trace(f'{sfol}Video {sname} has DESC POS match: {str(or_match_desc)}')
            if not bool(or_match_base or or_match_titl or or_match_desc):
                suc = False
                Log.trace(f'{sfol}Video {sname} misses required tag matching \'{extag}\'. Skipped!',
                          LoggingFlags.EX_MISSING_TAGS)
        elif extag.startswith('-('):
            neg_matches = get_neg_and_group_matches(extag, tags_raw)
            for conf, td in zip((Config.check_title_neg, Config.check_description_neg), (vi.title, vi.description)):
                if conf and td:
                    for tmatch in match_text(extag, td, 'and'):
                        tmatch_s = tmatch[:30]
                        Log.trace(f'{sfol}Video {sname} has POST/DESC NEG match: {tmatch_s}')
                        if tmatch_s not in neg_matches:
                            neg_matches.append(f'{tmatch_s}...')
            if neg_matches:
                suc = False
                Log.info(f'{sfol}Video {sname} contains excluded tags combination \'{extag}\': {",".join(neg_matches)}. Skipped!',
                         LoggingFlags.EX_EXCLUDED_TAGS)
        else:
            negative = extag.startswith('-')
            my_extag = extag[1:] if negative else extag
            mtag = get_matching_tag(my_extag, tags_raw)
            for conf, td in zip(
                (Config.check_title_pos, Config.check_title_neg, Config.check_description_pos, Config.check_description_neg),
                (vi.title, vi.title, vi.description, vi.description)
            ):
                if conf and td and not mtag:
                    mtag = match_text(my_extag, td)
                    if mtag:
                        mtag = f'{mtag[:50]}...'
                        Log.trace(f'{sfol}Video {sname} has POST/DESC {"NEG" if negative else "POS"} match: {mtag}')
            if mtag is not None and negative:
                suc = False
                Log.info(f'{sfol}Video {sname} contains excluded tag \'{mtag}\'. Skipped!',
                         LoggingFlags.EX_EXCLUDED_TAGS)
            elif mtag is None and not negative:
                suc = False
                Log.trace(f'{sfol}Video {sname} misses required tag matching \'{my_extag}\'. Skipped!',
                          LoggingFlags.EX_MISSING_TAGS)
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
        tag = re_replace_symbols.sub('_', tag.replace('-', '').replace('\'', '').replace('.', ''))
        alias = TAG_ALIASES.get(tag)
        if alias is None and re_tags_to_process.match(tag) is None:
            continue

        tag = alias or tag

        if alias is None and re_tags_to_exclude.match(tag):
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
