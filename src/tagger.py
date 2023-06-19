# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from re import compile as re_compile
from typing import List, Optional, Dict

from defs import TAGS_CONCAT_CHAR, UTF8, Log, LoggingFlags, normalize_path, prefixp, ExtraConfig, re_replace_symbols

__all__ = (
    'filtered_tags', 'get_matching_tag', 'register_item_tags', 'try_parse_id_or_group', 'dump_item_tags', 'valid_extra_tag',
    'is_filtered_out_by_extra_tags', 'unite_separated_tags'
)

re_wtag = re_compile(r'^[^?*]*[?*].*?$')
re_idval = re_compile(r'^id=\d+?$')
re_uscore_mult = re_compile(r'_{2,}')
re_not_a_letter = re_compile(r'[^a-z]+')
# re_bracketed_tag = re_compile(r'^([^(]+)\(([^)]+)\).*$')
re_numbered_or_counted_tag = re_compile(r'^(?!rule_?\d+)(?:\d+?\+?)?([^\d]+?)(?:_\d+|s)?$')

re_tags_to_process = re_compile(
    r'^(?:.+?_warc.+?|(?:[a-z]+?_)?elf|drae.{3}|tent[a-z]{3}es|(?:bell[a-z]|sto[a-z]{4})_bul[a-z]{2,3}|inf[a-z]{5}n|egg(?:_[a-z]{3,9}|s)?|'
    r'[a-z]{4}hral_i.+?|(?:\d{1,2}\+?)?(?:boys?|girls?|fu[a-z]{2}(?:[a-z]{4}|s)?|in[d-v]{2}cts?)|succ[a-z]{4}|'
    r'bbw|dog|eel|f(?:acesitting|ur)|hmv|orc|pmv|tar|c(?:\.c\.|um)|d\.va|na\'vi|kai\'sa|gender.+?|'
    r'[^(]+\([^)]+\).*?|[a-z_\-]+\d+?|\d{2,4}[a-z_\-]+?|[a-z_]{2,15}sfm|[^_]+_pov|fu[a-z]{2}(?:/|_(?:on|with)_)[a-z]{4}|'
    r'[a-z][a-z_]{2,17}|[a-g]ea?st[a-z]{6}|[lapymg]{3})$'
)

re_tags_to_exclude = re_compile(
    r'^(?:'
    r'a(?:dult.*?|gain|hegao|l(?:iv.+?|l(?:_.+?|ian.+?|lsex|ons?)?)|mazons?|n(?:gl.+?|im.+?)|poca.*?|r(?:che.*?|eol.*?|mor|t)|'  # a
    r's(?:ian.*?|s(?:ault|job)?)|thlet.*?|udi[bo].*?)|'  # a
    r'b(?:a(?:be.*?|ck.*?|ll.*?|re.*?|th.*?)|e(?:hind|lly)|i(?:g(?:[^j].+?)?|kin.+?)|l(?:end.*?|o(?:nd.*?|w[^j].*?)|ue.*?)|'  # b
    r'o(?:d[iy].*?|o[bt].*?|ss.*?|ttom.*?|unc.+?)|r(?:e(?:ast.*?|ed.*?)|o[tw].*?|unet.+?)|u(?:kk.*?|lg.+?|nny.*?|st.*?|tt.*?))|'  # b
    r'c(?:a(?:ge.*?|ni(?:d|ne|s)|p(?:i?tai?n|tur.+?)|r[rt].*?|v[ei].*?)|e(?:lebr.+?|nsor.+?)|'  # c
    r'h(?:a(?:ir|lleng.*?|mbers?|ract.+?|t.*?)|eat.*?|ines.*?|ok.*?|ub.+?)|ity|l(?:ap.*?|im.+?|o(?:n.+?|th.*?|wn.*?))|'  # c
    r'o(?:ck.*?|lor.*?|m[ip].+?|n(?:[dv].+?|sens.*?)|uch|w.+?)|r(?:e[as].+?|ing.*?|o(?:ss.*?|uch.*?))|'  # c
    r'u(?:lt.*?|m.+?|nn?[ai].*?|rv.+?|t[ei].*?))|'  # c
    r'd(?:a(?:tass|ughter.*?)|ccomi.*?|e(?:ad[^_]?.*?|cens.+?|ep.*?|feat.*?)|i(?:ck.*?|ffer.*?|rt.*?|s(?:cipl.+?|eas.*?))|'  # d
    r'o(?:ct.+?|gg.*?|ubl.+?)|r[iu]nk.*?|u[abo].*?)|'  # d
    r'e(?:ncoun.*?|rec.+?|v(?:il.?audio|ol.+?)|x(?:c(?:ess.*?|it.+?|lus.*?)|hibit.*?|p(?:er.+?|os.*?))|ye.+?)|'  # e
    r'f(?:a(?:c[et].*?|n(?:do.+?|ta.+?))|e(?:et.*?|line|male.*?|rtil.*?|tish.*?)|i(?:l[lm].*?|n(?:ale.*?|ger.*?|ish.*?))|'  # f
    r'l(?:ash.*?|uid.*?)|oot.*?|r(?:eckl.*?|iend.*?|om.*?)|u(?:ck.*?|rry..+?|ta(?:_on_[^m].+?|nari(?:_on_|on)[^m].+?|on[^m].+?)))|'  # f
    r'g(?:ame.*?|irl.*?|l(?:a[ns]s.*?|o(?:r.+?|ve.*?)|yph.*?)|oal.*?|rop.+?|uy.*?|ym.*?)|'  # g
    r'h(?:a(?:ir.*?|nd.*?|pp.*?|rds.+?)|e(?:art.*?|nta.*?)|o(?:l[do].*?|me.*?|ok.*?|rd(?!core).+?|us.+?)|u(g[eg].*?|man.*?)|ybrid)|'  # h
    r'i(?:mpreg.*?|n(?:side.*?|ter[nrs].*?))|'  # i
    r'j(?:a[ck]u.+?|erk.*?|iggl.*?|uic.+?)|'  # j
    r'k(?:iss.*?|not.*?)|'  # k
    r'l(?:a(?:cta.+?|rge.*?)|e(?:ak.*?|g.+?|otar.+?)|i(?:ck(?:ing)?|ft.*?|nger.*?|p.+?)|o(?:ck.*?|n[dg].*?|ok.*?))|'  # l
    r'm(?:a(?:chin.+?|de|gaz.*?|ke.*?|le.*?|rr[iy].*?|s(?:sag.+?|t(?:rub.+?|urb.+?))|t[ei].*?)|e(?:me.*?|ss.*?)|'  # m
    r'i(?:lk.*?|mic.*?|ni.*?|ssion.*?)|md|o(?:[ao]n.+?|d(?:e.*?)?|ld.*?|m|saic|ther)|p4|u(?:ltipl.+?|s(?:c[lu].+?|ic.*?)))|'  # m
    r'n(?:a(?:ke.+?|rra.+?|ught.*?)|e(?:ko.*?|tor.+?)|ipp.+?|o(?:_.+?|sound)|sfw.*?|tr|ud[ei].*?)|'  # n
    r'o(?:bey.*?|il.+?|n.+?|perat.*?|riginal.*?|ut.*?)|'  # o
    r'p(?:a(?:iz.+?|nt.*?|r(?:asite|[ot].*?))|e(?:n(?:et.+?|i.+?)|tite)|i(?:erc.*?|gtail.*?|ll.*?|n[bn].+?)|l(?:ay.*?|ea.*?)|'  # p
    r'o(?:nytail.*?|ol.*?|rn.*?|si.*?|und.*?)|r(?:e(?:dat.*?|mak.*?|view.*?)|inc.+?|o(?:ject.*?|n.+?|stit.*?))|u(?:bl?i.*?|ss.*?))|'  # p
    r'r(?:34|63|aid.*?|e(?:al.*?|boo.+?|d(?!head).+?|vers.+?)|i(?:d[ei].*?|mm.*?|s[ei].*?|tual.*?)|'  # r
    r'o(?:le.*?|man.*?|om.*?|ugh.*?)|u(?:bb.+?|le.*?))|'  # r
    r's(?:ans|chool.*?|ex.*?|fm|h(?:e|in[ey]|o(?:e.*?|rt.*?|uld.*?))|i(?:lver.*?|m(?:s[^\d].*?|ulat.+?)|nthet.*?|ster.*?|ze.*?)|'  # s
    r'l(?:ap.*?)|m(?:all.*?|il.+?|oth.+?)|o(?:ft.*?|mes?|u(?:nd.*?|rce.*?))|p(?:an[ik].*?|ort.*?)|q(?:u(?:ea.+?|irt.*?))|'  # s
    r't(?:a(?:nd.*?|r.*?)|ep.*?|o(?:ck.*?|ma.*?|r.*?)|raigh.+?|ud.*?|yl.+?)|u(?:bm.+?|per.*?)|w(?:eat.*?|i(?:m.*?|ng.*?)))|'  # s
    r't(?:a(?:g.+?|il.*?|lk.*?|n.+?|tt?o.*?)|e(?:as.+?|mpl.*?|st.*?)|h(?:i(?:c(?:c+|k)?|gh.*?)|rou.+?)|i(?:ktok.*?|t.+?)|'  # t
    r'o(?:e.+?|ilet|mb.*?|ngue.*?|on.*?|uch.*?)|pr|r(?:ain.*?|ip.*?|oug.+?)|win.*?)|'  # t
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
    re_compile(r'(?:(the),)?(l(?:ast|egend)),(of),(us|zelda)'): r'\1 \2 \3 \4',
    re_compile(r'(?:(the),)?(elder|owl|walking),(dead|house|scrolls)'): r'\1 \2 \3',
    re_compile(r'([^,]+),(a(?:nd|t)|for|i[ns]|o[fnr]|x|with),([^,]+)'): r'\1 \2 \3',
    re_compile(r'(three|f(?:o(?:re|ur)|ive)|\d+?),(some)'): r'\1\2',
    re_compile(r'([^,]+),(job)'): r'\1\2',
    re_compile(r'([^,]+),(man)'): r'\1 \2',
    re_compile(r'([^\d,]+),(0?\d)'): r'\1 \2',
    re_compile(r'(ada),(wong)'): r'\1 \2',
    re_compile(r'(all),(fours?)'): r'\1 \2',
    re_compile(r'(all),(the),(way),(thr(?:ough|u))'): r'\1 \2 \3 \4',
    re_compile(r'(alyx),(vance)'): r'\1 \2',
    re_compile(r'(aunt),(cass)'): r'\1 \2',
    re_compile(r'(azur),(lane)'): r'\1 \2',
    re_compile(r'(american),(dad)'): r'\1 \2',
    re_compile(r'(apex),(legends?)'): r'\1 \2',
    re_compile(r'(ashley),(graham|williams)'): r'\1 \2',
    re_compile(r'(atomic),(heart)'): r'\1 \2',
    re_compile(r'(avatar),(the),(last),(airbender)'): r'\1 \2 \3 \4',
    re_compile(r'(azure?),(lane)'): r'\1 \2',
    re_compile(r'(belly),(bulge)'): r'\1 \2',
    re_compile(r'(blue),(archive)'): r'\1 \2',
    re_compile(r'(breasts?|clit|dick|hyper|muscles?|penis),(expansion|growth|inflation)'): r'\1 \2',
    re_compile(r'(carlos),(oliveira)'): r'\1 \2',
    re_compile(r'(cassie),(cage)'): r'\1 \2',
    re_compile(r'(claire),(redfield)'): r'\1 \2',
    re_compile(r'(code),(geass?)'): r'\1 \2',
    re_compile(r'(c[ou]m+ing),(soon)'): r'\1 \2',
    re_compile(r'(cum),(shot)'): r'\1\2',
    re_compile(r'(cyberpunk),(2077|edgerunners?)'): r'\1 \2',
    re_compile(r'(black),(widow)'): r'\1 \2',
    re_compile(r'(blood|d(?:ark|row)|high|night|void),(el(?:f|ves?))'): r'\1 \2',
    re_compile(r'(danny),(phantom)'): r'\1 \2',
    re_compile(r'(dat),(ass)'): r'\1 \2',
    re_compile(r'(dogg?y),(style)'): r'\1 \2',
    re_compile(r'(dragon),(ballz?)'): r'\1\2',
    re_compile(r'(eggs?),((?:impl|inse|lay).*?)'): r'\1 \2',
    re_compile(r'(fap),(hero)'): r'\1 \2',
    re_compile(r'(fate),(grand),(order)'): r'\1 \2 \3',
    re_compile(r'(final),(fantasy)(?:,([\dxvi]{1,6}))?'): r'\1 \2 \3',
    re_compile(r'(fire),(emblem)'): r'\1 \2',
    re_compile(r'(first),(try|work)'): r'\1 \2',
    re_compile(r'(genshin),(impact)'): r'\1 \2',
    re_compile(r'(gang),((?:bang|rape))'): r'\1\2',
    re_compile(r'(grand),(cupido)'): r'\1\2',
    re_compile(r'(group),(sex)'): r'\1 \2',
    re_compile(r'(hagen),(toons)'): r'\1 \2',
    re_compile(r'(hard),(core)'): r'\1\2',
    re_compile(r'(harle?y),(quinn?)'): r'\1 \2',
    re_compile(r'(high),(heels?)'): r'\1 \2',
    re_compile(r'(highschool),(dxd)'): r'\1 \2',
    re_compile(r'(high),(school),(dxd)'): r'\1\2 \3',
    re_compile(r'(horse),(cock)'): r'\1 \2',
    re_compile(r'(hotel),(tran.+)'): r'\1 \2',
    re_compile(r'(jaina),(proudmoore)'): r'\1 \2',
    re_compile(r'(jennifer),(walters)'): r'\1 \2',
    re_compile(r'(jessie),(rasberry)'): r'\1 \2',
    re_compile(r'(jill),(valentine)'): r'\1 \2',
    re_compile(r'(jojo)(?:,(.?s))?,(bizzare),(adventure)'): r'\1\2 \3 \4',
    re_compile(r'(judy),(alvare[sz])'): r'\1 \2',
    re_compile(r'(kantai),(collection)'): r'\1 \2',
    re_compile(r'(kim),(possible)'): r'\1 \2',
    re_compile(r'(kono),(subarashii)'): r'\1 \2',
    re_compile(r'(lady|princess),([^,]+)'): r'\1 \2',
    re_compile(r'(lara),(croft)'): r'\1 \2',
    re_compile(r'(little),(witch),(academia)'): r'\1 \2 \3',
    re_compile(r'(lisa),(hamilton)'): r'\1 \2',
    re_compile(r'(marie),(rose)'): r'\1 \2',
    re_compile(r'(mass),(effect)'): r'\1 \2',
    re_compile(r'(merle),(nyalentine)'): r'\1 \2',
    re_compile(r'(mia),(winters?)'): r'\1 \2',
    re_compile(r'(milk),(factory)'): r'\1 \2',
    re_compile(r'(monster),(girls?|hunter)'): r'\1 \2',
    re_compile(r'(mortal),([ck]ombat)'): r'\1 \2',
    re_compile(r'(my),(life),(as),(?:(a),)?([^,]+),([^,]+)'): r'\1 \2 \3 \4 \5 \6',
    re_compile(r'(my),(life),(as),(?:(a),)?([^,]+)'): r'\1 \2 \3 \4 \5',
    re_compile(r'(my),(little),(pony)'): r'\1 \2 \3',
    re_compile(r'(nier),(automata)'): r'\1 \2',
    re_compile(r'(no),([^,]+)'): r'\1 \2',
    re_compile(r'(one),(p(?:iece|unch))'): r'\1 \2',
    re_compile(r'(rachel),(roth)'): r'\1 \2',
    re_compile(r'(resident),(evil)(?:,(village|0?\d))?'): r'\1 \2 \3',
    re_compile(r'(rey),(skywalker)'): r'\1 \2',
    re_compile(r'(rick),(and),(morty)'): r'\1 \2 \3',
    re_compile(r'(rock),(candy)'): r'\1 \2',
    re_compile(r'(salvatore),(moreau)'): r'\1 \2',
    re_compile(r'(samus),(aran)'): r'\1 \2',
    re_compile(r'(second),(li[fv]e)'): r'\1 \2',
    re_compile(r'(senran),(kagura)'): r'\1 \2',
    re_compile(r'(sheva),(alomar)'): r'\1 \2',
    re_compile(r'(silent),(hill)(?:,(0?\d))'): r'\1 \2 \3',
    re_compile(r'(soft),(core)'): r'\1\2',
    re_compile(r'(soul),(calibur|eater)'): r'\1 \2',
    re_compile(r'(spider),(man)'): r'\1 \2',
    re_compile(r'(star),(wars)(?:,(0?\d))?'): r'\1 \2 \3',
    re_compile(r'(stomach),(bulge)'): r'\1 \2',
    re_compile(r'(street),(fighter)'): r'\1 \2',
    re_compile(r'(sword),(art)(?:,(online))?'): r'\1 \2 \3',
    re_compile(r'(teen),(titans)'): r'\1 \2',
    re_compile(r'(the),(witcher)'): r'\2',
    re_compile(r'(tied),(down|feet|hands?|up)'): r'\1 \2',
    re_compile(r'(tifa),(lockhart)'): r'\1 \2',
    re_compile(r'(tina),(armstrong)'): r'\1 \2',
    re_compile(r'(tinker),(bell)'): r'\1 \2',
    re_compile(r'(triss),(merigold)'): r'\1 \2',
    re_compile(r'(vam),(guy)'): r'\1 \2',
    re_compile(r'(voice),(act[^,]*?)'): r'\1 \2',
    re_compile(r'(yorra),((?:comm?and|\d+)[^,]+)'): r'\1 \2',
    re_compile(r'(yuffie),(kisa[^,]+?)'): r'\1 \2',
    re_compile(r'(wander),(over),(yonder)'): r'\1 \2 \3',
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
    'genderswap_(mtf)': 'genderswap_mtf',
    'genderswap_(ftm)': 'genderswap_ftm',
}


def valid_extra_tag(tag: str) -> str:
    try:
        if tag[0] == '(':
            assert_valid_or_group(tag)
        elif tag.startswith('-('):
            validate_neg_and_group(tag)
        else:
            pass
        return tag.lower().replace(' ', '_')
    except Exception:
        Log.fatal(f'Fatal: invalid tags group: \'{tag}\'!')
        raise ValueError


def is_non_wtag(tag: str) -> bool:
    return not re_wtag.fullmatch(tag)


def is_valid_neg_and_group(andgr: str) -> bool:
    return (len(andgr) >= len('-(.,.)') and andgr.startswith('-(') and andgr.endswith(')')
            and andgr.find(',') != -1 and len(andgr[2:-1].split(',', 1)) == 2)


def validate_neg_and_group(andgr: str) -> None:
    assert is_valid_neg_and_group(andgr)


def is_valid_or_group(orgr: str) -> bool:
    return len(orgr) >= len('(.~.)') and orgr[0] == '(' and orgr[-1] == ')' and orgr.find('~') != -1 and len(orgr[1:-1].split('~', 1)) == 2


def assert_valid_or_group(orgr: str) -> None:
    assert is_valid_or_group(orgr)


def normalize_wtag(wtag: str) -> str:
    for c in '.[]()-+':
        wtag = wtag.replace(c, f'\\{c}')
    return wtag.replace('*', '.*').replace('?', '.')


def get_matching_tag(wtag: str, mtags: List[str]) -> Optional[str]:
    if is_non_wtag(wtag):
        return wtag if wtag in mtags else None
    pat = re_compile(rf'^{normalize_wtag(wtag)}$')
    for htag in mtags:
        if pat.fullmatch(htag):
            return htag
    return None


def get_or_group_matching_tag(orgr: str, mtags: List[str]) -> Optional[str]:
    assert_valid_or_group(orgr)
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
        return all(re_idval.fullmatch(tag) for tag in orgr[1:-1].split('~'))
    return False


def try_parse_id_or_group(ex_tags: List[str]) -> List[int]:
    if len(ex_tags) == 1:
        orgr = ex_tags[0]
        if is_valid_id_or_group(orgr):
            return [int(tag.replace('id=', '')) for tag in orgr[1:-1].split('~')]
    return []


def trim_undersores(base_str: str) -> str:
    return re_uscore_mult.sub('_', base_str).strip('_')


def is_filtered_out_by_extra_tags(idi: int, tags_raw: List[str], extra_tags: List[str], is_extra_seq: bool, subfolder: str) -> bool:
    suc = True
    sname = f'{prefixp()}{idi:d}.mp4'
    if len(extra_tags) > 0:
        if is_extra_seq:
            assert len(extra_tags) == 1
            id_sequence = try_parse_id_or_group(extra_tags)
            assert id_sequence
            if idi not in id_sequence:
                suc = False
                Log.trace(f'[{subfolder}] Video {sname} isn\'t contained in id list \'{str(id_sequence)}\'. Skipped!',
                          LoggingFlags.LOGGING_EX_MISSING_TAGS)
            return not suc

        for extag in extra_tags:
            if extag[0] == '(':
                if get_or_group_matching_tag(extag, tags_raw) is None:
                    suc = False
                    Log.trace(f'[{subfolder}] Video {sname} misses required tag matching \'{extag}\'. Skipped!',
                              LoggingFlags.LOGGING_EX_MISSING_TAGS)
            elif extag.startswith('-('):
                if is_neg_and_group_matches(extag, tags_raw):
                    suc = False
                    Log.info(f'[{subfolder}] Video {sname} contains excluded tags combination \'{extag[1:]}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
            else:
                my_extag = extag[1:] if extag[0] == '-' else extag
                mtag = get_matching_tag(my_extag, tags_raw)
                if mtag is not None and extag[0] == '-':
                    suc = False
                    Log.info(f'[{subfolder}] Video {sname} contains excluded tag \'{mtag}\'. Skipped!',
                             LoggingFlags.LOGGING_EX_EXCLUDED_TAGS)
                elif mtag is None and extag[0] != '-':
                    suc = False
                    Log.trace(f'[{subfolder}] Video {sname} misses required tag matching \'{my_extag}\'. Skipped!',
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


def filtered_tags(tags_list: List[str]) -> str:
    if len(tags_list) == 0:
        return ''

    tags_list_final = []  # type: List[str]

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


saved_tags_dict = dict()  # type: Dict[str, Dict[int, str]]


def register_item_tags(item_id: int, tags_str: str, subfolder: str) -> None:
    if subfolder not in saved_tags_dict.keys():
        saved_tags_dict[subfolder] = dict()
    saved_tags_dict[subfolder][item_id] = tags_str


def dump_item_tags() -> None:
    """Saves tags for each subfolder in scenario and base dest folder based on registered item tags dict"""
    for subfolder, tags_dict in saved_tags_dict.items():
        if len(tags_dict) == 0:
            continue
        min_id, max_id = min(tags_dict.keys()), max(tags_dict.keys())
        fullpath = f'{normalize_path(f"{ExtraConfig.dest_base}{subfolder}")}{prefixp()}!tags_{min_id:d}-{max_id:d}.txt'
        with open(fullpath, 'wt', encoding=UTF8) as sfile:
            sfile.writelines(f'{prefixp()}{idi:d}: {tags.strip()}\n' for idi, tags in sorted(tags_dict.items(), key=lambda t: t[0]))

#
#
#########################################
