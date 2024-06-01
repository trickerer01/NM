# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from re import compile as re_compile
from typing import Pattern

from defs import QUALITIES, EXTENSIONS_V, PREFIX

# common
re_media_filename = re_compile(fr'^(?:{PREFIX})?(\d+).*?(?:_({"|".join(QUALITIES)}))?\.(?:{"|".join(EXTENSIONS_V)})$')
re_infolist_filename = re_compile(fr'{PREFIX}!(?:tag|description|comment)s_\d+-\d+\.txt')
re_replace_symbols = re_compile(r'[^0-9a-zA-Z.,_+%!\-()\[\] ]+')
re_ext = re_compile(r'(\.[^&]{3,5})&')
re_private_video = re_compile(r'^This is a private video\..*?$')
# pages
re_page_entry = re_compile(r'^/video/(\d+)/[^/]+?$')
# re_page_rating = re_compile(r'^(?:\d{1,3}%|-)$')
# re_page_title = re_compile(r'^video-title title-truncate.*?$')
# validators
re_non_search_symbols = re_compile(r'[^\da-zA-Z._+\-\[\]]')
re_session_id = re_compile(r'[a-z0-9]{26}')
# tagger
re_wtag = re_compile(r'^[^?*]*[?*].*?$')
re_idval = re_compile(r'^id=\d+?$')
re_uscore_mult = re_compile(r'_{2,}')
re_not_a_letter = re_compile(r'[^a-z]+')
# re_bracketed_tag = re_compile(r'^([^(]+)\(([^)]+)\).*?$')
re_numbered_or_counted_tag = re_compile(r'^(?!rule_?\d+)(?:\d+?\+?)?([^\d]+?)(?:_\d+|s)?$')
re_or_group = re_compile(r'^\([^~]+(?:~[^~]+)+\)$')
re_neg_and_group = re_compile(r'^-\([^,]+(?:,[^,]+)+\)$')

re_tags_to_process = re_compile(
    r'^(?:.+?_warc.+?|(?:[a-z]+?_)?elf|drae.{3}|tent[a-z]{3}es|(?:bell[a-z]|sto[a-z]{4})_bul[a-z]{2,3}|inf[a-z]{5}n|egg(?:_[a-z]{3,9}|s)?|'
    r'[a-z]{4}hral_i.+?|(?:\d{1,2}\+?)?(?:boys?|girls?|fu[a-z]{2}(?:[a-z]{4}|s)?|in[d-v]{2}cts?|monsters?)|succ[a-z]{4}|'
    r'bbw|dog|eel|f(?:acesitting|ur)|orc|hmv|pmv|tar|c(?:\.c\.|um)|d\.va|na\'vi|kai\'sa|gender.+?|'
    r'[^(]+\([^)]+\).*?|[a-z_\-]+\d+?|\d{2,4}[a-z_\-]+?|[a-z_]{2,15}sfm|[^_]+_pov|(?:fu|s)[a-z]{6}(?:/|_(?:on|with)_)[a-z]{4}(?:oy)?|'
    r'[a-z][a-z_]{2,17}|[a-g]ea?st[a-z]{6}|[lapymg]{3})$'
)
re_tags_to_exclude = re_compile(
    r'^(?:'
    r'a(?:cted|dult.*?|gain|hegao|l(?:iv.+?|l(?:_.+?|ian.+?|lsex|ons?)?)|mazons?|n(?:gl.+?|im.+?)|poca.*?|r(?:che.*?|eol.*?|mor|t)|'  # a
    r's(?:ian.*?|s(?:ault|job)?)|thlet.*?|udi[bo].*?)|'  # a
    r'b(?:a(?:be.*?|ck.*?|ll.*?|re.*?|th.*?)|e(?:hind|lly)|i(?:g(?:[^j].+?)?|kin.+?)|l(?:end.*?|o(?:nd.*?|w[^j].*?)|ue.*?)|'  # b
    r'o(?:d[iy].*?|o[bt].*?|ss.*?|ttom.*?|unc.+?)|r(?:e(?:ast.*?|ed.*?)|o[tw].*?|unet.+?)|u(?:kk.*?|lg.+?|nny.*?|st.*?|tt.*?))|'  # b
    r'c(?:a(?:ge.*?|ni(?:d|ne|s)|p(?:i?tai?n|tur.+?)|r[rt].*?|v[ei].*?)|e(?:lebr.+?|nsor.+?)|'  # c
    r'h(?:a(?:ir|lleng.*?|mbers?|ract.+?|t.*?)|eat.*?|ines.*?|ok.*?|ub.+?)|ity|l(?:ap.*?|im.+?|o(?:n.+?|th.*?|wn.*?))|'  # c
    r'o(?:ck.*?|lor.*?|m[ip].+?|n(?:[dv].+?|sens.*?)|uch|w.+?)|r(?:e[as].+?|ing.*?|o(?:ss.*?|uch.*?))|'  # c
    r'u(?:lt.*?|m.+?|nn?[ai].*?|rv.+?|t[ei].*?))|'  # c
    r'd(?:a(?:tass|ughter.*?)|ccomi.*?|e(?:ad[^_]?.*?|cens.+?|ep.*?|feat.*?)|i(?:ck.*?|ffer.*?|rt.*?|s(?:cipl.+?|eas.*?))|'  # d
    r'o(?:ct.+?|gg.*?|ubl.+?)|r[iu]nk.*?|u[abo].*?)|'  # d
    r'e(?:ffect.*?|ncoun.*?|rec.+?|v(?:il.?audio|ol.+?)|x(?:c(?:ess.*?|it.+?|lus.*?)|hibit.*?|p(?:er.+?|os.*?))|ye.+?)|'  # e
    r'f(?:a(?:c[et].*?|n(?:do.+?|ta.+?))|e(?:et.*?|line|male.*?|rtil.*?|tish.*?)|i(?:l[lm].*?|n(?:ale.*?|ger.*?|ish.*?))|'  # f
    r'l(?:ash.*?|uid.*?)|o(?:cus.*?|ot.*?)|r(?:eckl.*?|iend.*?|om.*?)|'  # f
    r'u(?:ck.*?|rry..+?|ta(?:_on_[^m].+?|nari(?:_on_|on)[^m].+?|on[^m].+?)))|'  # f
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
    r'p(?:a(?:iz.+?|nt.*?|r(?:asite|[ot].*?))|e(?:n(?:et.+?|i.+?)|tite)|h(?:one)|i(?:erc.*?|gtail.*?|ll.*?|n[bn].+?)|l(?:ay.*?|ea.*?)|'  # p
    r'o(?:nytail.*?|ol.*?|rn.*?|si.*?|und.*?)|r(?:e(?:dat.*?|mak.*?|view.*?)|inc.+?|o(?:ject.*?|n.+?|stit.*?))|u(?:bl?i.*?|ss.*?))|'  # p
    r'r(?:34|63|aid.*?|e(?:al.*?|boo.+?|d(?!head).+?|vers.+?)|i(?:d[ei].*?|mm.*?|s[ei].*?|tual.*?)|'  # r
    r'o(?:le.*?|man.*?|om.*?|ugh.*?)|u(?:bb.+?|le.*?))|'  # r
    r's(?:ans|c(?:hool.*?|reen.*?)|ex.*?|fm|h(?:e|in[ey]|o(?:e.*?|rt.*?|uld.*?))|'  # s
    r'i(?:lver.*?|m(?:s[^\d].*?|ulat.+?)|nthet.*?|ster.*?|ze.*?)|kin|l(?:ap.*?)|m(?:all.*?|il.+?|oth.+?)|'  # s
    r'o(?:ft.*?|mes?|u(?:nd.*?|rce.*?))|p(?:an[ik].*?|ort.*?)|q(?:u(?:ea.+?|irt.*?))|'  # s
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
    re_compile(r'(mrs?)\.?,(x)(?:,|$)'): r'\1.\2',
    re_compile(r'(?:(the),)?(l(?:ast|egend)),(of),(us|zelda)'): r'\1 \2 \3 \4',
    re_compile(r'(?:(the),)?(elder|owl|walking),(dead|house|scrolls)'): r'\1 \2 \3',
    re_compile(r'([^,]+),(a(?:nd|t)|for|i[ns]|o[fnr]|x|with),([^,]+)'): r'\1 \2 \3',
    re_compile(r'(t(?:hree|wo)|f(?:o(?:re|ur)|ive)|\d+?),(some)(?:,|$)'): r'\1\2',
    re_compile(r'(fore|horse|pony),(girls?|plays?)(?:,|$)'): r'\1\2',
    re_compile(r'(bl(?:ack|ue)|dark|gre(?:en|y)|pale|p(?:ink|urple)|white),(skin)'): r'\1 \2',
    re_compile(r'([^,]+),(job)(?:,|$)'): r'\1\2',
    re_compile(r'([^,]+),(boys?|girls?|m[ae]n)(?:,|$)'): r'\1 \2',
    re_compile(r'([^\d,]+),(\d+)(?:,|$)'): r'\1 \2',
    re_compile(r'(ada),(wong)'): r'\1 \2',
    re_compile(r'(against),(?:(the),)?(desk|table|wall)'): r'\1 the \3',
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
    re_compile(r'(baldur(?:\'?s)?),(gate)(?:,(\d))?(?:,|$)'): r'\1 \2 \3',
    re_compile(r'(being),([a-z]+ed)'): r'\1 \2',
    re_compile(r'(belly),(bulge)'): r'\1 \2',
    re_compile(r'(big),(hero),(\d)?(?:,|$)'): r'\1 \2 \3',
    re_compile(r'(black),(widow)'): r'\1 \2',
    re_compile(r'(blood|d(?:ark|row)|high|night|void),(el(?:f|ves?))'): r'\1 \2',
    re_compile(r'(blue),(archive)'): r'\1 \2',
    re_compile(r'(breasts?|clit|dick|hyper|muscles?|penis),(expansion|growth|inflation)'): r'\1 \2',
    re_compile(r'(cammy),(white)'): r'\1 \2',
    re_compile(r'(carlos),(oliveira)'): r'\1 \2',
    re_compile(r'(cassie),(cage)'): r'\1 \2',
    re_compile(r'(claire),(redfield)'): r'\1 \2',
    re_compile(r'(code),(geass?)'): r'\1 \2',
    re_compile(r'(c[ou]m+ing),(soon)'): r'\1 \2',
    re_compile(r'(cum),(shot)'): r'\1\2',
    re_compile(r'(cyberpunk),(2077|edgerunners?)'): r'\1 \2',
    re_compile(r'(danny),(phantom)'): r'\1 \2',
    re_compile(r'(darth),(maul|vader)'): r'\1 \2',
    re_compile(r'(dat),(ass)'): r'\1 \2',
    re_compile(r'(detroit),(become),(human)'): r'\1 \2 \3',
    re_compile(r'(dogg?y),(style)'): r'\1 \2',
    re_compile(r'(dragon),(ballz?)'): r'\1\2',
    re_compile(r'(eggs?),((?:impl|inse|lay)[^,]+)'): r'\1 \2',
    re_compile(r'(emma),(watson)'): r'\1 \2',
    re_compile(r'(fap),(hero)'): r'\1 \2',
    re_compile(r'(fate),(grand),(order)'): r'\1 \2 \3',
    re_compile(r'(final),(fantasy)(?:,([\dxvi]{1,6}))?'): r'\1 \2 \3',
    re_compile(r'(fire),(emblem)'): r'\1 \2',
    re_compile(r'(first),(try|work)'): r'\1 \2',
    re_compile(r'(genshin),(impact)'): r'\1 \2',
    re_compile(r'(gang),((?:bang|rape))'): r'\1\2',
    re_compile(r'(grand),(cupido)'): r'\1\2',
    re_compile(r'(group),(sex)(?:,|$)'): r'\1 \2',
    re_compile(r'(g[uvw]en),(stac[iuy])'): r'\1 \2',
    re_compile(r'(hagen),(toons)'): r'\1 \2',
    re_compile(r'(hana),(song)'): r'\1 \2',
    re_compile(r'(hard),(core)'): r'\1\2',
    re_compile(r'(harle?y),(quinn?)'): r'\1 \2',
    re_compile(r'(high),(heels?)'): r'\1 \2',
    re_compile(r'(highschool),(dxd)'): r'\1 \2',
    re_compile(r'(high),(school),(dxd)'): r'\1\2 \3',
    re_compile(r'(honey),(select)'): r'\1 \2',
    re_compile(r'(horse),(cock)'): r'\1 \2',
    re_compile(r'(hotel),(tran.+)'): r'\1 \2',
    re_compile(r'(jaina),(proudmoore)'): r'\1 \2',
    re_compile(r'(jedi),(fallen),(order)'): r'\1 \2 \3',
    re_compile(r'(jennifer),(walters)'): r'\1 \2',
    re_compile(r'(jessie),(rasberry)'): r'\1 \2',
    re_compile(r'(jill),(valentine)'): r'\1 \2',
    re_compile(r'(jojo)(?:,(.?s))?,(bizzare),(adventure)'): r'\1\2 \3 \4',
    re_compile(r'(judy),(alvare[sz]|panam)'): r'\1 \2',
    re_compile(r'(jur[iy]),(han)'): r'\1 \2',
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
    re_compile(r'(mind),(break)'): r'\1 \2',
    re_compile(r'(monster),(girls?|hunter)'): r'\1 \2',
    re_compile(r'(mortal),([ck]ombat)'): r'\1 \2',
    re_compile(r'(my),(life),(as),(?:(a),)?([^,]+),([^,]+)'): r'\1 \2 \3 \4 \5 \6',
    re_compile(r'(my),(life),(as),(?:(a),)?([^,]+)'): r'\1 \2 \3 \4 \5',
    re_compile(r'(my),(little),(pony)'): r'\1 \2 \3',
    re_compile(r'(nier),(automata)'): r'\1 \2',
    re_compile(r'(no),([^,]+)'): r'\1 \2',
    re_compile(r'(one),(p(?:iece|unch))'): r'\1 \2',
    re_compile(r'(queen),(nualia|oph?ali?a)'): r'\1 \2',
    re_compile(r'(rachel),(roth)'): r'\1 \2',
    re_compile(r'(resident),(evil)(?:,(village|\d))?(?:,|$)'): r'\1 \2 \3',
    re_compile(r'(rey),(skywalker)'): r'\1 \2',
    re_compile(r'(red),(head)'): r'\1\2',
    re_compile(r'(rick),(and),(morty)'): r'\1 \2 \3',
    re_compile(r'(rock),(candy)'): r'\1 \2',
    re_compile(r'(salvatore),(moreau)'): r'\1 \2',
    re_compile(r'(samus),(aran)'): r'\1 \2',
    re_compile(r'(second),(li[fv]e)'): r'\1 \2',
    re_compile(r'(senran),(kagura)'): r'\1 \2',
    re_compile(r'(science),(fiction)'): r'\1 \2',
    re_compile(r'(sheva),(alomar)'): r'\1 \2',
    re_compile(r'(silent),(hill)(?:,(\d))?(?:,|$)'): r'\1 \2 \3',
    re_compile(r'(sleepy),(b)'): r'\1 \2',
    re_compile(r'(soft),(core)'): r'\1\2',
    re_compile(r'(soul),(calibur|eater)'): r'\1 \2',
    re_compile(r'(spider),(man)'): r'\1 \2',
    re_compile(r'(star),(wars)(?:,(\d))?(?:,|$)'): r'\1 \2 \3',
    re_compile(r'(stomach),(bulge)'): r'\1 \2',
    re_compile(r'(street),(fighter)'): r'\1 \2',
    re_compile(r'(sword),(art)(?:,(online))?'): r'\1 \2 \3',
    re_compile(r'(tali),(zorah)'): r'\1 \2',
    re_compile(r'(teen),(titans)'): r'\1 \2',
    re_compile(r'(the),(incredibles|sims|witch(?:er)?)(?:,(\d))?(?:,|$)'): r'\2 \3',
    re_compile(r'(tied),(down|feet|hands?|legs?|up)'): r'\1 \2',
    re_compile(r'(tifa),(lockhart)'): r'\1 \2',
    re_compile(r'(tina),(armstrong)'): r'\1 \2',
    re_compile(r'(tinker),(bell)'): r'\1 \2',
    re_compile(r'(triss),(merigold)'): r'\1 \2',
    re_compile(r'(vam),(guy)'): r'\1 \2',
    re_compile(r'(voice),(act[^,]*?)'): r'\1 \2',
    re_compile(r'(wander),(over),(yonder)'): r'\1 \2 \3',
    re_compile(r'(wonder),(woman)'): r'\1 \2',
    re_compile(r'(yorra),((?:comm?and|\d+)[^,]+)'): r'\1 \2',
    re_compile(r'(yuffie),(kisa[^,]+?)'): r'\1 \2',
}


# in-place
def prepare_regex_fullmatch(raw_string: str) -> Pattern[str]:
    return re_compile(rf'^{raw_string}$')

#
#
#########################################
