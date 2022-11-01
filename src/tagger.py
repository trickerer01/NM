# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from re import compile as re_compile, fullmatch as re_fullmatch, match as re_match, sub as re_sub
from typing import List, Optional

from defs import TAGS_CONCAT_CHAR, Log

re_replace_symbols = re_compile(
    r'[^0-9a-zA-Z_+()\[\]]+'
)

# used with re.sub
# noinspection RegExpAnonymousGroup
re_numbered_or_counted_tag = re_compile(
    r'^(?!rule_?\d+)(?:\d+?\+?)?([^\d]+?)(?:_\d+|s)?$'
)

re_tags_to_process = re_compile(
    r'^(?:.+?_warc.+?|(?:[a-z]+?_)?elf|drae.{3}|tent[a-z]{3}es|(?:bell[a-z]|sto[a-z]{4})_bul[a-z]{2,3}|inf[a-z]{5}n|egg(?:_[a-z]{3,9}|s)?|'
    r'[a-z]{4}hral_i.+?|(?:\d{1,2}\+?)?(?:boys?|girls?|fu[a-z]{2}(?:[a-z]{4}|s)?|in[d-v]{2}cts?)|succ[a-z]{4}|'
    r'bbw|dog|eel|f(?:acesitting|ur)|hmv|orc|pmv|tar|c(?:\.c\.|um)|d\.va|na\'vi|kai\'sa|'
    r'[^(]+\([^)]+\).*?|[a-z_\-]+\d+?|\d{2,4}[a-z_\-]+?|[a-z_]{2,15}sfm|[^_]+_pov|fu[a-z]{2}(?:/|_(?:on|with)_)[a-z]{4}|'
    r'[a-z][a-z_]{2,17}|[a-g]ea?st[a-z]{6}|[lapymg]{3})$'
)

re_tags_to_exclude = re_compile(
    r'^(?:'
    r'a(?:dult.*?|gain|hegao|l(?:iv.+?|l(?:_.+?|ian.+?|lsex|ons?)?)|mazons?|n(?:gl.+?|im.+?)|poca.*?|r(?:che.*?|eol.*?|mor)|'  # a
    r's(?:ian.*?|s(?:ault|job)?)|udi[bo].*?)|'  # a
    r'b(?:a(?:be.*?|ck.*?|ll.*?|re.*?|th.*?)|e(?:hind|lly)|i(?:g(?:[^j].+?)?|kin.+?)|l(?:end.*?|o(?:nd.*?|w[^j].*?)|ue.*?)|'  # b
    r'o(?:d[iy].*?|o[bt].*?|ss.*?|ttom.*?|unc.+?)|r(?:e(?:ast.*?|ed.*?)|o[tw].*?|unet.+?)|u(?:kk.*?|lg.+?|nny.*?|st.*?|tt.*?))|'  # b
    r'c(?:a(?:ge.*?|ni.+?|p(?:i?tai?n|tur.+?)|r[rt].*?|v[ei].*?)|e(?:lebr.+?|nsor.+?)|'  # c
    r'h(?:a(?:ir|lleng.*?|mbers?|ract.+?|t.*?)|eat.*?|ines.*?|ok.*?|ub.+?)|ity|l(?:ap.*?|im.+?|o(?:n.+?|th.*?|wn.*?))|'  # c
    r'o(?:ck.*?|lor.*?|m[ip].+?|n(?:[dv].+?|sens.*?)|uch|w.+?)|r(?:e[as].+?|ing.*?|oss.*?)|u(?:lt.*?|m.+?|nn?[ai].*?|rv.+?|t[ei].*?))|'  # c
    r'd(?:a(?:tass|ughter.*?)|ccomi.*?|e(?:ad[^_]?.*?|cens.+?|ep.*?|feat.*?)|i(?:ck.*?|ffer.*?|rt.*?|s(?:cipl.+?|eas.*?))|'  # d
    r'o(?:ct.+?|gg.*?|ubl.+?)|r[iu]nk.*?|u[bo].*?)|'  # d
    r'e(?:ncoun.*?|rec.+?|vol.+?|x(?:c(?:ess.*?|it.+?|lus.*?)|hibit.*?|p(?:er.+?|os.*?))|ye.+?)|'  # e
    r'f(?:a(?:c[et].*?|n(?:do.+?|ta.+?))|e(?:et.*?|line|male.*?|tish.*?)|i(?:l[lm].*?|n(?:ale.*?|ger.*?|ish.*?))|'  # f
    r'l(?:ash.*?|uid.*?)|oot.*?|r(?:eckl.*?|iend.*?|om.*?)|u(?:ck.*?|rry..+?|ta(?:_on_[^m].+?|nari(?:_on_|on)[^m].+?|on[^m].+?)))|'  # f
    r'g(?:ame.*?|irl.*?|l(?:a[ns]s.*?|o(?:r.+?|ve.*?)|yph.*?)|oal.*?|rop.+?|uy.*?|ym.*?)|'  # g
    r'h(?:a(?:ir.*?|nd.*?|pp.*?|rds.+?)|e(?:art.*?|nta.*?)|o(?:l[do].*?|me.*?|ok.*?|rd(?!core).+?|us.+?)|u(g[eg].*?|man.*?)|ybrid)|'  # h
    r'i(?:mpreg.*?|n(?:side.*?|ter[nrs].*?))|'  # i
    r'j(?:a[ck]u.+?|erk.*?)|'  # j
    r'k(?:iss.*?|not.*?)|'  # k
    r'l(?:acta.+?|e(?:ak.*?|g.+?|otar.+?)|i(?:ck(?:ing)?|ft.*?|nger.*?|p.+?)|o(?:ck.*?|n[dg].*?|ok.*?))|'  # l
    r'm(?:a(?:chin.+?|de|gaz.*?|ke.*?|le.*?|rr[iy].*?|s(?:sag.+?|t(?:rub.+?|urb.+?))|t[ei].*?)|e(?:me.*?|ss.*?)|'  # m
    r'i(?:lk.*?|mic.*?|ni.*?|ssion.*?)|md|o(?:[ao]n.+?|de.*?|ld.*?|m|saic|ther)|p4|u(?:ltipl.+?|s(?:c[lu].+?|ic.*?)))|'  # m
    r'n(?:a(?:ke.+?|rra.+?|ught.*?)|e(?:ko.*?|tor.+?)|ipp.+?|o(?:_.+?|sound)|sfw.*?|tr|ud[ei].*?)|'  # n
    r'o(?:bey.*?|il.+?|n.+?|perat.*?|riginal.*?|ut.*?)|'  # o
    r'p(?:a(?:iz.+?|nt.*?|r(?:asite|[ot].*?))|e(?:n(?:et.+?|i.+?)|tite)|i(?:erc.*?|gtail.*?|ll.*?|n[bn].+?)|l(?:ay.*?|ea.*?)|'  # p
    r'o(?:nytail.*?|ol.*?|rn.*?|si.*?|und.*?)|r(?:e(?:dat.*?|mak.*?|view.*?)|inc.+?|o(?:ject.*?|n.+?|stit.*?))|u(?:bl?i.*?|ss.*?))|'  # p
    r'r(?:34|63|aid.*?|e(?:al.*?|boo.+?|d(?!head).+?|vers.+?)|i(?:d[ei].*?|mm.*?|s[ei].*?|tual.*?)|'  # r
    r'o(?:le.*?|man.*?|om.*?|ugh.*?)|u(?:bb.+?|le.*?))|'  # r
    r's(?:ans|chool.*?|ex.*?|fm|h(?:e|o(?:e.*?|rt.*?))|i(?:lver.*?|m(?:s[^\d].*?|ulat.+?)|nthet.*?|ster.*?|ze.*?)|lap.*?|'  # s
    r'm(?:all.*?|il.+?|oth.+?)|o(?:ft.*?|mes?|u(?:nd.*?|rce.*?))|p(?:an[ik].*?|ort.*?)|q(?:u(?:ea.+?|irt.*?))|'  # s
    r't(?:a(?:nd.*?|r.*?)|ep.*?|o(?:ck.*?|ma.*?|r.*?)|raigh.+?|ud.*?|yl.+?)|u(?:bm.+?|per.*?)|w(?:eat.*?|i(?:m.*?|ng.*?)))|'  # s
    r't(?:a(?:g.+?|il.*?|lk.*?|n.+?|tt?o.*?)|e(?:as.+?|mpl.*?|st.*?)|h(?:i(?:c(?:c+|k)?|gh.*?)|rou.+?)|i(?:ktok.*?|t.+?)|'  # t
    r'o(?:e.+?|ilet|mb.*?|ngue.*?|on.*?|uch.*?)|r(?:ain.*?|ip.*?|oug.+?)|win.*?)|'  # t
    r'u(?:ltra.*?|n[cdw].+?)|'  # u
    r'v(?:a(?:gi.+?|m(?:_guy)?)|ery.*?|i(?:de.+?|rt(?:amat.*?|ual.*?))|o(?:ice.*?|lkor)|r.+?|tub.*?)|'  # v
    r'w(?:a(?:lk.*?|n[kt].*?)|e(?:b.+?|t)|hat.*?|i(?:[df]e.*?|th_.+?)|o(?:l[fv].+?|m[ae]n|rk.*?)|rit.+?|tf)|'  # w
    r'x(?:vid.*?)|'  # x
    r'y(?:ou.+?)|'  # y
    r'\d{1,5}_?(?:\+?(?:(?:fe)?males?|boys?|girls?)|d|fps|p|s(?:ecs?_.+?)?)?'  # 0-9
    r')$'
)

RAW_TAGS_REPLACEMENTS = {
    re_compile(r'(with),(sound)'): r'\1 \2',
    re_compile(r'(strap),(on)'): r'\1\2',
    re_compile(r'(mr),(\.?x)'): r'\1\2',
    re_compile(r'(?:(the),)?(legend),(of),(zelda)'): r'\1 \2 \3 \4',
    re_compile(r'([^,]+),(a(?:nd|t)|for|in|o[fnr]|with),([^,]+)'): r'\1 \2 \3',
    re_compile(r'(three|f(?:o(?:re|ur)|ive)|\d+?),(some)'): r'\1\2',
    re_compile(r'([^,]+),(job)'): r'\1\2',
    re_compile(r'(ada),(wong)'): r'\1 \2',
    re_compile(r'(all),(fours?)'): r'\1 \2',
    re_compile(r'(all),(the),(way),(thr(?:ough|u))'): r'\1 \2 \3 \4',
    re_compile(r'(apex),(legends?)'): r'\1 \2',
    re_compile(r'(azure?),(lane)'): r'\1 \2',
    re_compile(r'(belly),(bulge)'): r'\1 \2',
    re_compile(r'(cassie),(cage)'): r'\1 \2',
    re_compile(r'(claire),(redfield)'): r'\1 \2',
    re_compile(r'(c[ou]m+?ing),(soon)'): r'\1 \2',
    re_compile(r'(cum),(shot)'): r'\1\2',
    re_compile(r'(black),(widow)'): r'\1 \2',
    re_compile(r'(blood|d(?:ark|row)|high|night|void),(el(?:f|ves?))'): r'\1 \2',
    re_compile(r'(dat),(ass)'): r'\1 \2',
    re_compile(r'(dogg?y),(style)'): r'\1 \2',
    re_compile(r'(dragon),(ballz?)'): r'\1\2',
    re_compile(r'(fap),(hero)'): r'\1 \2',
    re_compile(r'(fate),(grand),(order)'): r'\1 \2 \3',
    re_compile(r'(final),(fantasy)(?:,(x[^,]{2}))?'): r'\1 \2 \3',
    re_compile(r'(first),(try|work)'): r'\1 \2',
    re_compile(r'(genshin),(impact)'): r'\1 \2',
    re_compile(r'(gang),((?:bang|rape))'): r'\1\2',
    re_compile(r'(grand),(cupido)'): r'\1\2',
    re_compile(r'(group),(sex)'): r'\1 \2',
    re_compile(r'(hard),(core)'): r'\1\2',
    re_compile(r'(harle?y),(quinn?)'): r'\1 \2',
    re_compile(r'(horse),(cock)'): r'\1\2',
    re_compile(r'(jaina),(proudmoore)'): r'\1 \2',
    re_compile(r'(jill),(valentine)'): r'\1 \2',
    re_compile(r'(kantai),(collection)'): r'\1 \2',
    re_compile(r'(lady),([^,]+)'): r'\1 \2',
    re_compile(r'(lara),(croft)'): r'\1 \2',
    re_compile(r'(lisa),(hamilton)'): r'\1 \2',
    re_compile(r'(marie),(rose)'): r'\1 \2',
    re_compile(r'(mia),(winters?)'): r'\1 \2',
    re_compile(r'(monster),(girls?)'): r'\1 \2',
    re_compile(r'(mortal),([ck]ombat)'): r'\1 \2',
    re_compile(r'(my),(little),(pony)'): r'\1 \2 \3',
    re_compile(r'(nier),(automata)'): r'\1 \2',
    re_compile(r'(no),([^,]+)'): r'\1 \2',
    re_compile(r'(resident),(evil),(village|\d)'): r'\1 \2 \3',
    re_compile(r'(resident),(evil)'): r'\1 \2',
    re_compile(r'(salvatore),(moreau)'): r'\1 \2',
    re_compile(r'(samus),(aran)'): r'\1 \2',
    re_compile(r'(second),(li[fv]e)'): r'\1 \2',
    re_compile(r'(sheva),(alomar)'): r'\1 \2',
    re_compile(r'(soft),(core)'): r'\1\2',
    re_compile(r'(stomach),(bulge)'): r'\1 \2',
    re_compile(r'(street),(fighter)'): r'\1 \2',
    re_compile(r'(the),(witcher)'): r'\2',
    re_compile(r'(tied),(down|feet|hands?|up)'): r'\1 \2',
    re_compile(r'(tifa),(lockhart)'): r'\1 \2',
    re_compile(r'(tina),(armstrong)'): r'\1 \2',
    re_compile(r'(triss),(merigold)'): r'\1 \2',
    re_compile(r'(vam),(guy)'): r'\1 \2',
    re_compile(r'(voice),(act[^,]*)'): r'\1 \2',
    re_compile(r'(yorra),((?:comm?and|\d+)[^,]+)'): r'\1 \2',
}

TAG_ALIASES = {
    'sfmpmv': 'pmv',
    'sfmhmv': 'hmv',
    'analsex': 'anal',
    'apexlegend': 'apex_legends',
    'apexlegends': 'apex_legends',
    'bistiality': 'bestiality',
    'bestyality': 'bestiality',
    'bistyality': 'bestiality',
    'caning': 'bondage',
    'handcuffs': 'bondage',
    'handcuff': 'bondage',
    'imprisoned': 'bondage',
    'cuffs': 'bondage',
    'restraint': 'bondage',
    'restraints': 'bondage',
    'shackle': 'bondage',
    'shackles': 'bondage',
    'cat_girl': 'catgirl',
    'cassiecage': 'cassie_cage',
    'deadoralive': 'dead_or_alive',
    'doa': 'dead_or_alive',
    '1futa': 'futa',
    '2futa': 'futa',
    '3futa': 'futa',
    '1futas': 'futa',
    '2futas': 'futa',
    '3futas': 'futa',
    '4futas': 'futa',
    'dickgirl': 'futa',
    'futaxfuta': 'futa',
    'futaonfuta': 'futa',
    'futawithfuta': 'futa',
    'futaxfemale': 'futa',
    'futaonfemale': 'futa',
    'futawithfemale': 'futa',
    'futaxfutanari': 'futa',
    'futaonfutanari': 'futa',
    'futawithfutanari': 'futa',
    'futa_on_futa': 'futa',
    'futa_with_futa': 'futa',
    'futa_on_female': 'futa',
    'futa_with_female': 'futa',
    'futa_on_futanari': 'futa',
    'futa_with_futanari': 'futa',
    'futanarixfuta': 'futa',
    'futanarionfuta': 'futa',
    'futanariwithfuta': 'futa',
    'futanarixfemale': 'futa',
    'futanarionfemale': 'futa',
    'futanariwithfemale': 'futa',
    'futanarixfutanari': 'futa',
    'futanarionfutanari': 'futa',
    'futanariwithfutanari': 'futa',
    'futanari_on_futa': 'futa',
    'futanari_with_futa': 'futa',
    'futanari_on_female': 'futa',
    'futanari_with_female': 'futa',
    'futanari_on_futanari': 'futa',
    'futanari_with_futanari': 'futa',
    'futanarixmale': 'futa_on_male',
    'futanarionmale': 'futa_on_male',
    'futanariwithmale': 'futa_on_male',
    'futanari_on_male': 'futa_on_male',
    'futanari_with_male': 'futa_on_male',
    'futaxmale': 'futa_on_male',
    'futaonmale': 'futa_on_male',
    'futawithmale': 'futa_on_male',
    'futa_on_male': 'futa_on_male',
    'futa_with_male': 'futa_on_male',
    'futanarixboy': 'futa_on_male',
    'futanarionboy': 'futa_on_male',
    'futanariwithboy': 'futa_on_male',
    'futanari_on_boy': 'futa_on_male',
    'futanari_with_boy': 'futa_on_male',
    'futaxboy': 'futa_on_male',
    'futaonboy': 'futa_on_male',
    'futawithboy': 'futa_on_male',
    'futa_on_boy': 'futa_on_male',
    'futa_with_boy': 'futa_on_male',
    'futanarixguy': 'futa_on_male',
    'futanarionguy': 'futa_on_male',
    'futanariwithguy': 'futa_on_male',
    'futanari_on_guy': 'futa_on_male',
    'futanari_with_guy': 'futa_on_male',
    'futaxguy': 'futa_on_male',
    'futaonguy': 'futa_on_male',
    'futawithguy': 'futa_on_male',
    'futa_on_guy': 'futa_on_male',
    'futa_with_guy': 'futa_on_male',
    'malexfuta': 'male_on_futa',
    'maleonfuta': 'male_on_futa',
    'malewithfuta': 'male_on_futa',
    'male_on_futa': 'male_on_futa',
    'male_with_futa': 'male_on_futa',
    'malexfutanari': 'male_on_futa',
    'maleonfutanari': 'male_on_futa',
    'malewithfutanari': 'male_on_futa',
    'male_on_futanari': 'male_on_futa',
    'male_with_futanari': 'male_on_futa',
    'guyxfuta': 'male_on_futa',
    'guyonfuta': 'male_on_futa',
    'guywithfuta': 'male_on_futa',
    'guy_on_futa': 'male_on_futa',
    'guy_with_futa': 'male_on_futa',
    'guyxfutanari': 'male_on_futa',
    'guyonfutanari': 'male_on_futa',
    'guywithfutanari': 'male_on_futa',
    'guy_on_futanari': 'male_on_futa',
    'guy_with_futanari': 'male_on_futa',
    'boyxfuta': 'male_on_futa',
    'boyonfuta': 'male_on_futa',
    'boywithfuta': 'male_on_futa',
    'boy_on_futa': 'male_on_futa',
    'boy_with_futa': 'male_on_futa',
    'boyxfutanari': 'male_on_futa',
    'boyonfutanari': 'male_on_futa',
    'boywithfutanari': 'male_on_futa',
    'boy_on_futanari': 'male_on_futa',
    'boy_with_futanari': 'male_on_futa',
    'dominant': 'domination',
    'dominated': 'domination',
    'dominating': 'domination',
    'dragonballz': 'dragonball',
    'dragon_ballz': 'dragonball',
    'dragon_ball_z': 'dragonball',
    'dragonball_z': 'dragonball',
    'finalfantasy': 'final_fantasy',
    'final_fantasy_xiv': 'final_fantasy',
    'ffxiv': 'final_fantasy',
    'gangrape': 'gangbang',
    'gang_rape': 'gangbang',
    'gang_bang': 'gangbang',
    'group': 'orgy',
    'groupsex': 'orgy',
    'group_sex': 'orgy',
    'threesome': 'orgy',
    'thresome': 'orgy',
    'foursome': 'orgy',
    'foresome': 'orgy',
    'fivesome': 'orgy',
    '3some': 'orgy',
    '4some': 'orgy',
    '5some': 'orgy',
    'leagueoflegends': 'league_of_legends',
    'jillvalentine': 'jill_valentine',
    'claireredfield': 'claire_redfield',
    'trissmerigold': 'triss_merigold',
    'laracroft': 'lara_croft',
    'jaina': 'jaina_proudmoore',
    'jainaproudmoore': 'jaina_proudmoore',
    'marierose': 'marie_rose',
    'metroid': 'samus_aran',
    'residentevil': 'resident_evil',
    'samusaran': 'samus_aran',
    'streetfighter': 'street_fighter',
    'mortalcombat': 'mortal_combat',
    'secondlife': 'second_life',
    'secondlive': 'second_life',
    'second_live': 'second_life',
    'stomach_bulge': 'belly_bulge',
    'sucking': 'oral',
    'suck': 'oral',
    'wow': 'world_of_warcraft',
    'worldwarcraft': 'world_of_warcraft',
    'worldofwarcraft': 'world_of_warcraft',
    'whore': 'slut',
    'blowjob': 'oral',
    'lezdom': 'lesbian',
}


def is_non_wtag(tag: str) -> bool:
    return not re_fullmatch(r'^[^?*]*[?*].*?$', tag)


def is_valid_neg_and_group(andgr: str) -> bool:
    return (len(andgr) >= len('-(.,.)') and andgr.startswith('-(') and andgr.endswith(')') and
            andgr.find(',') != -1 and len(andgr[2:-1].split(',', 1)) == 2)


def validate_neg_and_group(andgr: str) -> None:
    assert is_valid_neg_and_group(andgr)


def is_valid_or_group(orgr: str) -> bool:
    return len(orgr) >= len('(.~.)') and orgr[0] == '(' and orgr[-1] == ')' and orgr.find('~') != -1 and len(orgr[1:-1].split('~', 1)) == 2


def validate_or_group(orgr: str) -> None:
    assert is_valid_or_group(orgr)


def get_matching_tag(wtag: str, mtags: List[str]) -> Optional[str]:
    if not is_non_wtag(wtag):
        escaped_tag = (
            wtag.replace('.', '\\.').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('-', '\\-')
            .replace('*', '.*').replace('?', '.')
        )
        pat = re_compile(rf'^{escaped_tag}$')
        for htag in mtags:
            if re_fullmatch(pat, htag):
                return htag
        return None
    else:
        return wtag if wtag in mtags else None


def get_or_group_matching_tag(orgr: str, mtags: List[str]) -> Optional[str]:
    validate_or_group(orgr)
    for tag in orgr[1:-1].split('~'):
        mtag = get_matching_tag(tag, mtags)
        if mtag:
            return mtag
    return None


def is_neg_and_group_matches(andgr: str, mtags: List[str]) -> bool:
    validate_neg_and_group(andgr)
    return all(get_matching_tag(wtag, mtags) is not None for wtag in andgr[2:-1].split(','))


def is_valid_id_or_group(orgr: str) -> bool:
    if is_valid_or_group(orgr):
        return all(re_fullmatch(r'^id=\d+?$', tag) for tag in orgr[1:-1].split('~'))
    return False


def try_parse_id_or_group(ex_tags: List[str]) -> Optional[List[int]]:
    if len(ex_tags) == 1:
        orgr = ex_tags[0]
        if is_valid_id_or_group(orgr):
            return [int(tag.replace('id=', '')) for tag in orgr[1:-1].split('~')]
    return None


def trim_undersores(base_str: str) -> str:
    ret_str = re_sub(r'_{2,}', '_', base_str)
    if len(ret_str) != 0:
        if len(ret_str) >= 2 and ret_str[0] == '_' and ret_str[-1] == '_':
            ret_str = ret_str[1:-1]
        elif ret_str[-1] == '_':
            ret_str = ret_str[:-1]
        elif ret_str[0] == '_':
            ret_str = ret_str[1:]
    return ret_str


def unite_separated_tags(comma_separated_tags_str: str) -> str:
    words = comma_separated_tags_str
    for raw_tag_replacement_re, raw_tag_replacement_groups in RAW_TAGS_REPLACEMENTS.items():
        try:
            words = re_sub(raw_tag_replacement_re, raw_tag_replacement_groups, words)
        except Exception:
            Log(f'Unable to apply \'{str(raw_tag_replacement_re)}\' with groups\'{raw_tag_replacement_groups}\' to string \'{words}\'\n'
                f'!Orig was: \'{comma_separated_tags_str}\'!')
            continue
    return words


def filtered_tags(tags_list: List[str]) -> str:
    if len(tags_list) == 0:
        return ''

    # tag_chars = '!abcdefghijklmnopqrstuvwxyz'
    # tags_dict = {c: [] for c in tag_chars}  # type: Dict[str, List[str]]
    tags_list_final = []  # type: List[str]

    for tag in tags_list:
        tag = re_sub(re_replace_symbols, '_', tag)
        if TAG_ALIASES.get(tag) is None and re_match(re_tags_to_process, tag) is None:
            continue

        alias = TAG_ALIASES.get(tag)
        if alias:
            tag = alias

        if re_match(re_tags_to_exclude, tag):
            continue

        tag = trim_undersores(tag)

        # tag_char = tag[0] if tag[0] in tag_chars[1:] else tag_chars[0]
        do_add = True
        if len(tags_list_final) > 0:
            # try and see
            # 1) if this tag can be consumed by existing tags
            # 2) if this tag can consume existing tags
            for i in reversed(range(len(tags_list_final))):
                t = re_sub(re_numbered_or_counted_tag, r'\1', tags_list_final[i].lower())
                if len(t) >= len(tag) and (tag in t):
                    do_add = False
                    break
            if do_add:
                for i in reversed(range(len(tags_list_final))):
                    t = re_sub(re_numbered_or_counted_tag, r'\1', tags_list_final[i].lower())
                    if len(tag) >= len(t) and (t in tag):
                        del tags_list_final[i]
        if do_add:
            for i, c in enumerate(tag):  # type: int, str
                if (i == 0 or tag[i - 1] == '_') and c.isalpha():
                    tag = f'{tag[:i]}{c.upper()}{tag[i + 1:]}'
            tags_list_final.append(tag)

    # tags_list_final = []
    # [tags_list_final.extend(tag_list) for tag_list in tags_dict.values() if len(tag_list) != 0]

    return trim_undersores(TAGS_CONCAT_CHAR.join(tags_list_final))

#
#
#########################################
