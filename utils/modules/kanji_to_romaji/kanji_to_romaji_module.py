# coding=utf-8
import os
import sys
from collections import OrderedDict

try:
    # noinspection PyPackageRequirements
    import simplejson as json
except ImportError:
    import json

from .models import UnicodeRomajiMapping
from .models import KanjiBlock
from .models import Particle

PATH_TO_MODULE = os.path.dirname(__file__)
JP_MAPPINGS_PATH = os.path.join(PATH_TO_MODULE, "jp_mappings")

hiragana_iter_mark = "ゝ"
hiragana_voiced_iter_mark = "ゞ"
katakana_iter_mark = "ヽ"
katakana_voiced_iter_mark = "ヾ"
kanji_iteration_mark = "々"

hirgana_soukon_unicode_char = "っ"
katakana_soukon_unicode_char = "ッ"
katakana_long_vowel_mark = "ー"


def load_kana_mappings_dict():
    kana_romaji_mapping = {}
    for f in os.listdir(JP_MAPPINGS_PATH):
        if os.path.splitext(f)[1] == ".json" and "kanji" not in f:
            with open(os.path.join(JP_MAPPINGS_PATH, f), encoding='utf-8-sig') as data_file:
                kana_romaji_mapping.update(json.load(data_file))
    return kana_romaji_mapping


def load_kanji_mappings_dict():
    """
    read through all json files that contain "kanji" in filename
    load json data from files to kanji_romaji_mapping dictionary
    if the key(kanji char) has already been added to kanji_romaji_mapping then create "other_readings" key
        "other_readings" will consist of w_type for its key and the new romaji reading for it
        e.g:
            {u"係り":
                'w_type': 'noun',
                'romaji': 'kakari',
                {'other_readings': {'godan verb stem': 'kakawari'}
            }
    :return: dict - kanji to romaji mapping
    """

    kanji_romaji_mapping = {}
    f_list = os.listdir(JP_MAPPINGS_PATH)
    for f in f_list[:]:  # shift all conjugated files to end, lower priority for verb stems
        if "conjugated" in f:
            f_list.remove(f)
            f_list.append(f)

    for f in f_list:
        if os.path.splitext(f)[1] == ".json" and "kanji" in f:
            with open(os.path.join(JP_MAPPINGS_PATH, f), encoding='utf-8-sig') as data_file:
                data_file_dict = json.load(data_file)
                for k in list(data_file_dict.keys()):
                    if k in kanji_romaji_mapping and \
                                    data_file_dict[k]["w_type"] != kanji_romaji_mapping[k]["w_type"]:
                        # if "other_readings" in kanji_romaji_mapping[k] and \
                        #                 data_file_dict[k]["w_type"] in kanji_romaji_mapping[k]["other_readings"]:
                        #     raise

                        if "other_readings" not in kanji_romaji_mapping[k]:
                            kanji_romaji_mapping[k]["other_readings"] = {}

                        kanji_romaji_mapping[k]["other_readings"][data_file_dict[k]["w_type"]] = \
                            data_file_dict[k]["romaji"]
                    else:
                        kanji_romaji_mapping[k] = data_file_dict[k]
    return kanji_romaji_mapping


def _convert_hira_kata_char(hira_or_kata_char, h_to_k=True):
    """
    take second last hex character from unicode and add/subtract 6 hex to it to get hiragana/katakana char
    e.g hiragana u3041 -> 0x3041 + 0x6 = 0x30A1 -> katakana u30A1

    :param hira_or_kata_char: unicode hiragana character
    :return: converterd hiragana or katakana depending on h_to_k value
    """
    if h_to_k:
        suffix_offset = 6
    else:
        suffix_offset = -6
    unicode_second_last_char = list(hira_or_kata_char.encode("unicode_escape"))[-2]
    suffix = hex(int(unicode_second_last_char, 16) + suffix_offset)
    char_list = list(hira_or_kata_char.encode("unicode_escape"))
    char_list[-2] = suffix[-1]
    result_char = "".join(char_list).decode('unicode-escape').encode('utf-8')
    return result_char


def convert_hiragana_to_katakana(hiragana):
    converted_str = ""

    for c in hiragana:
        if is_hiragana(c) or c in [hiragana_iter_mark, hiragana_voiced_iter_mark, hirgana_soukon_unicode_char]:
            converted_str += _convert_hira_kata_char(c)
        else:
            converted_str += c.encode('utf-8')
    return converted_str.decode("utf-8")


def convert_katakana_to_hiragana(katakana):
    converted_str = ""

    for c in katakana:
        if is_katakana(c) or c in [katakana_iter_mark, katakana_voiced_iter_mark,
                                   katakana_soukon_unicode_char]:
            converted_str += _convert_hira_kata_char(c, h_to_k=False)
        else:
            converted_str += c.encode('utf-8')
    return converted_str.decode("utf-8")


def is_hiragana(c):
    hiragana_starting_unicode = "\u3041"
    hiragana_ending_unicode = "\u3096"
    return c not in [hiragana_iter_mark, hiragana_voiced_iter_mark, hirgana_soukon_unicode_char] and \
        hiragana_starting_unicode <= c <= hiragana_ending_unicode


def is_katakana(c):
    katakana_starting_unicode = "\u30A1"
    katakana_ending_unicode = "\u30F6"
    return c not in [katakana_iter_mark, katakana_voiced_iter_mark,
                     katakana_soukon_unicode_char, katakana_long_vowel_mark] and \
        katakana_starting_unicode <= c <= katakana_ending_unicode


def is_kanji(c):
    cjk_start_range = "\u4E00"
    cjk_end_range = "\u9FD5"
    if isinstance(c, KanjiBlock):
        return True
    else:
        return c != kanji_iteration_mark and cjk_start_range <= c <= cjk_end_range


def get_char_type(c):
    """
    determine type of passed character by checking if it belongs in a certan unicode range
    :param c: kana or kanji character
    :return: type of character
    """
    char_type = None
    if is_hiragana(c):
        char_type = "hiragana"
    elif is_katakana(c):
        char_type = "katakana"
    elif is_kanji(c):
        char_type = "kanji"

    return char_type


def translate_particles(kana_list):
    """
    try to find particles which are in hirgana and turn them in to Particle objects
    Particle will provide spacing and will be translated in to appropriate romaji (e.g wa instead of ha for は)

    rules (varies depending on the hiragana char):
        char between two KanjiBlocks(that can be nouns) then assume to be a particle
            e.g: 私は嬉 -> KanjiBlock(私), は, KanjiBlock(嬉) -> は is particle use wa instead of ha
        type(Kanji, Hiragana, Katakana) changes adjacent to the char
            e.g: アパートへくる -> ト, へ, く -> katakana, へ, hiragana -> へ is a particle, use e instead of he
        char is last char and previous char is a noun
            e.g: 会いました友達に -> KanjiBlock(友達) which is a noun, に

    :param kana_list: list of kana characters and KanjiBlock objects
    :return: None; update the kana_list that is passed
    """
    def is_noun(k_block):
        return hasattr(k_block, "w_type") and ("noun" in k_block.w_type or "pronoun" in k_block.w_type)

    def type_changes(p, n):
        if get_char_type(p) is not None and get_char_type(n) is not None:
            return get_char_type(p) != get_char_type(n)
        else:
            return False

    def particle_imm_follows(prev_c_, valid_prev_particles):
        """
        check if prev_c is a Particle object
        check that prev_c is one of the valid_prev_particles
        e.g: wa particle can't be followed by wa particle again but ni particle can be followed by wa.
        :param prev_c_: previous character compared to current character in the iteration
        :param valid_prev_particles: list of previous particles that can be followed by current character.
        :return:
        """
        return isinstance(prev_c_, Particle) and prev_c_ in valid_prev_particles

    no_hira_char = "\u306E"
    ha_hira_char = "\u306F"
    he_hira_char = "\u3078"
    to_hira_char = "\u3068"
    ni_hira_char = "\u306B"
    de_hira_char = "\u3067"
    mo_hira_char = "\u3082"
    ga_hira_char = "\u304C"

    no_prtcle = Particle("no")
    wa_prtcle = Particle("wa")
    e_prtcle = Particle("e")
    to_prtcle = Particle("to")
    ni_prtcle = Particle("ni")
    de_prtcle = Particle("de")
    mo_prtcle = Particle("mo")
    ga_prtcle = Particle("ga")

    for i in range(1, len(kana_list)):
        is_last_char = False
        prev_c = kana_list[i - 1]
        if i == len(kana_list) - 1:
            is_last_char = True
            next_c = ""
        else:
            next_c = kana_list[i + 1]

        if kana_list[i] == no_hira_char:
            if (is_noun(prev_c) and is_noun(next_c)) or \
                    type_changes(prev_c, next_c) or \
                    (is_noun(prev_c) and is_last_char):
                kana_list[i] = no_prtcle

        elif kana_list[i] == ha_hira_char:
            if (is_noun(prev_c) and isinstance(next_c, KanjiBlock)) or \
                    type_changes(prev_c, next_c) or \
                    particle_imm_follows(prev_c, [e_prtcle, to_prtcle, ni_prtcle, de_prtcle]) or \
                    (is_noun(prev_c) and is_last_char):
                kana_list[i] = wa_prtcle

        elif kana_list[i] == mo_hira_char:
            if (is_noun(prev_c) and isinstance(next_c, KanjiBlock)) or \
                    type_changes(prev_c, next_c) or \
                    particle_imm_follows(prev_c, [ni_prtcle, de_prtcle]) or \
                    (is_noun(prev_c) and is_last_char):
                kana_list[i] = mo_prtcle

        elif kana_list[i] in [he_hira_char, to_hira_char, ni_hira_char, de_hira_char, ga_hira_char] and \
                (is_noun(prev_c) and isinstance(next_c, KanjiBlock)) or \
                type_changes(prev_c, next_c) or \
                (is_noun(prev_c) and is_last_char):

            if kana_list[i] == he_hira_char:
                kana_list[i] = e_prtcle

            elif kana_list[i] == to_hira_char:
                kana_list[i] = to_prtcle

            elif kana_list[i] == ni_hira_char:
                kana_list[i] = ni_prtcle

            elif kana_list[i] == de_hira_char:
                kana_list[i] = de_prtcle

            elif kana_list[i] == ga_hira_char:
                kana_list[i] = ga_prtcle


def translate_kanji_iteration_mark(kana_list):
    """
    translate kanji_iteration_mark: 々
    e.g:
        在々: zaizai
    :param kana_list: unicode consisting of kana and kanji chars
    :return: unicode with kanji iteration marks translated
    """
    prev_c = ""
    for i in range(0, len(kana_list)):
        if kana_list[i] == kanji_iteration_mark:
            kana_list[i] = prev_c.romaji.strip()
        prev_c = kana_list[i]


def get_type_if_verb_stem(curr_chars):
    """
    get verb type for given verb stem. verb types can be ichidan, godan or None.
    No stem for irregulars
    :param curr_chars: kanji chars that is a verb stem
    :return: type of verb stem
    """
    v_type = None

    if "verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["w_type"]:
        v_type = UnicodeRomajiMapping.kanji_mapping[curr_chars]["w_type"]

    elif "other_readings" in UnicodeRomajiMapping.kanji_mapping[curr_chars]:
        if "godan verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]:
            v_type = "godan verb"
        elif "ichidan verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]:
            v_type = "ichidan verb"

    return v_type


def check_for_verb_stem_ending(kana_list, curr_chars, start_pos, char_len):
    """
    if the given curr_chars has a verb stem reading then try to match it with an one of the listed verb endings
    otherwise return/use its .romaji property

    e.g:
    kana_list = [KanjiBlock(灯り), ま, し, た]
    curr_chars = 灯り can be verb stem reading
    try and match 灯り with an ending within kana_list
    灯り + ました matches
    romaji is tomori + mashita (this modifies kana_list to remove matched ending)
    kana_list = [tomorimashita]

    kana_list = [KanjiBlock(灯り), を, 見ます]
    curr_chars = 灯り can be verb stem reading
    try and match 灯り with an ending within kana_list
    no matching ending
    romaji is akari
    kana_list = [akari, を, 見ます]

    :param kana_list:
    :param curr_chars: KanjiBlock current characters to parse out of entire kana_list
    :param start_pos:
    :param char_len:
    :return: ending kanji, ending romaji; both will be None if ending not found
    """
    endings = OrderedDict({})
    endings["ませんでした"] = "masen deshita"
    endings["ませんで"] = "masende"
    endings["なさるな"] = "nasaruna"
    endings["なかった"] = "nakatta"
    endings["れて"] = "rete"
    endings["ましょう"] = "mashou"
    endings["ました"] = "mashita"
    endings["まして"] = "mashite"
    endings["ません"] = "masen"
    endings["ないで"] = "naide"
    endings["なさい"] = "nasai"
    endings["ます"] = "masu"
    endings["よう"] = "you"  # ichidan
    endings["ない"] = "nai"
    endings["た"] = "ta"  # ichidan
    endings["て"] = "te"  # ichidan
    endings["ろ"] = "ro"  # ichidan
    endings["う"] = "u"

    dict_entry = None

    if "verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["w_type"]:
        dict_entry = UnicodeRomajiMapping.kanji_mapping[curr_chars]

    elif "other_readings" in UnicodeRomajiMapping.kanji_mapping[curr_chars]:

        if "godan verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]:
            dict_entry = {
                "romaji": UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]["godan verb stem"]
            }
        elif "ichidan verb stem" in UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]:
            dict_entry = {
                "romaji": UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"]["ichidan verb stem"]
            }
    e_k = None
    e_r = None
    if dict_entry is not None:
        for e in list(endings.keys()):
            possible_conj = curr_chars + e
            actual_conj = "".join(kana_list[start_pos: (start_pos + char_len + len(e))])
            if possible_conj == actual_conj:
                e_k = e
                e_r = endings[e] + " "
                break

    return e_k, e_r


def has_non_verb_stem_reading(curr_chars):
    """
    check if curr_chars has an alternative reading aside from the verb stem
    :param curr_chars: unicode kanji chars to check
    :return: true/false depending on if curr_chars has a verb stem reading
    """
    res = False

    if "verb stem" not in UnicodeRomajiMapping.kanji_mapping[curr_chars]["w_type"]:
        res = True

    elif "other_readings" in UnicodeRomajiMapping.kanji_mapping[curr_chars]:
        if any(["verb stem" not in ork
                for ork in list(UnicodeRomajiMapping.kanji_mapping[curr_chars]["other_readings"].keys())]):
            res = True

    return res


def get_verb_stem_romaji(verb_stem_kanji):
    """
    find romaji for verb stem within kanji_mapping
    :param verb_stem_kanji: unicode verb stem kanji
    :return: romaji for verb stem kanji
    """
    romaji = None
    if "verb stem" in UnicodeRomajiMapping.kanji_mapping[verb_stem_kanji]["w_type"]:
        romaji = UnicodeRomajiMapping.kanji_mapping[verb_stem_kanji]["romaji"]
    elif "other_readings" in UnicodeRomajiMapping.kanji_mapping[verb_stem_kanji]:
        for k in list(UnicodeRomajiMapping.kanji_mapping[verb_stem_kanji]["other_readings"].keys()):
            if "verb stem" in k:
                romaji = UnicodeRomajiMapping.kanji_mapping[verb_stem_kanji]["other_readings"][k]
                break

    return romaji


def prepare_kanjiblocks(kchar_list):
    """
    create and replace matched Kanji characters that are within kanji_mapping with KanjiBlock
    KanjiBlock will be used for spacing and particle translation later
    if the kanji found is a verb stem then try to find an ending to match it with what's in kchar_list
    :param kchar_list: list containing kana and kanji characters
    :return: kchar_list with all found Kanji characters turned in to KanjiBlock objects
    """
    if len(UnicodeRomajiMapping.kanji_mapping) == 0:
        UnicodeRomajiMapping.kanji_mapping = load_kanji_mappings_dict()

    max_char_len = len(kchar_list)
    kana_list = list(kchar_list)

    start_pos = 0
    while start_pos < max_char_len:
        char_len = len(kana_list) - start_pos
        while char_len > 0:
            curr_chars = "".join(kana_list[start_pos: (start_pos + char_len)])
            if curr_chars in UnicodeRomajiMapping.kanji_mapping:
                verb_stem_type = get_type_if_verb_stem(curr_chars)
                ending_match_found = False
                if verb_stem_type is not None:
                    ending_kana, ending_romaji = check_for_verb_stem_ending(kana_list, curr_chars, start_pos, char_len)
                    if ending_kana is not None and ending_romaji is not None:
                        ending_match_found = True
                        conjugated_val = {
                            "romaji": get_verb_stem_romaji(curr_chars) + ending_romaji,
                            "w_type": "conjugated " + verb_stem_type
                        }

                        for i in range(start_pos + char_len - 1 + len(ending_kana), start_pos - 1, -1):
                            del kana_list[i]

                        kana_list.insert(start_pos,
                                         KanjiBlock(curr_chars + ending_kana, conjugated_val))

                if ending_match_found is False and has_non_verb_stem_reading(curr_chars):
                    for i in range(start_pos + char_len - 1, start_pos - 1, -1):
                        del kana_list[i]
                    kana_list.insert(start_pos,
                                     KanjiBlock(curr_chars, UnicodeRomajiMapping.kanji_mapping[curr_chars]))
            char_len -= 1
        start_pos += 1
    return kana_list


def translate_kanji(kana_list):
    i = 0
    while i < len(kana_list):
        if type(kana_list[i]) == KanjiBlock:
            kana_list[i] = kana_list[i].romaji
        i += 1

    kana = "".join(kana_list)
    return kana


def prep_kanji(kana):
    kana_list = list(kana)
    if any([is_kanji(k) for k in kana]):
        kana_list = prepare_kanjiblocks(kana)
        translate_kanji_iteration_mark(kana_list)

    return kana_list


def translate_to_romaji(kana):
    """
    translate hiragana, katakana, typographic, and fhw latin
    :param kana: unicode kana(+kanji) characters
    :return: translated base kana characters to romaji as well as typographic, and fhw latin
    """
    if len(UnicodeRomajiMapping.kana_mapping) == 0:
        UnicodeRomajiMapping.kana_mapping = load_kana_mappings_dict()

    max_char_len = 2

    for char_len in range(max_char_len, 0, -1):
        start_pos = 0
        while start_pos < len(kana) - char_len + 1:
            curr_chars = kana[start_pos: (start_pos + char_len)]
            if curr_chars in UnicodeRomajiMapping.kana_mapping:
                kana = kana.replace(curr_chars, UnicodeRomajiMapping.kana_mapping[curr_chars], 1)
                if len(UnicodeRomajiMapping.kana_mapping[curr_chars]) == 0:
                    start_pos -= 1
            start_pos += 1

    while "  " in kana:
        kana = kana.replace("  ", " ")
    kana = kana.strip()

    lines = kana.split("\n")
    for i in range(0, len(lines)):
        lines[i] = lines[i].strip()
    kana = "\n".join(lines)
    return kana


def translate_soukon(partial_kana):
    """
    translate both hiragana and katakana soukon: っ, ッ; repeats next consonant
    e.g:
        ちょっと willl be choっto by the time iit is passed to this method and then becomes chotto
    :param partial_kana: partially translated kana with base kana chars already translated to romaji
    :return: partial kana with soukon translated
    """
    prev_char = ""

    for c in reversed(partial_kana):
        if c == hirgana_soukon_unicode_char or c == katakana_soukon_unicode_char:  # assuming that soukon can't be last
            partial_kana = prev_char[0].join(partial_kana.rsplit(c, 1))
        prev_char = c
    return partial_kana


def translate_long_vowel(partial_kana):
    """
    translate katakana long vowel ー; repeats previous vowel
    e.g:
        メール will be meーru by the time it is passed to this method and then becomes meeru
    :param partial_kana: partially translated kana with base kana chars already translated to romaji
    :return: partial kana with long vowel translated
    """
    prev_c = ""
    for c in partial_kana:
        if c == katakana_long_vowel_mark:
            if prev_c[-1] in list("aeiou"):
                partial_kana = partial_kana.replace(c, prev_c[-1], 1)
            else:
                partial_kana = partial_kana.replace(c, "", 1)
        prev_c = c
    return partial_kana


def translate_soukon_ch(kana):
    """
    if soukon(mini-tsu) is followed by chi then soukon romaji becomes 't' sound
    e.g: ko-soukon-chi -> kotchi instead of kocchi
    :param kana:
    :return:
    """

    prev_char = ""
    hiragana_chi_unicode_char = "\u3061"
    katakana_chi_unicode_char = "\u30C1"
    partial_kana = kana
    for c in reversed(kana):
        if c == hirgana_soukon_unicode_char or c == katakana_soukon_unicode_char:  # assuming that soukon can't be last
            if prev_char == hiragana_chi_unicode_char or prev_char == katakana_chi_unicode_char:
                partial_kana = "t".join(partial_kana.rsplit(c, 1))
        prev_char = c
    return partial_kana


def _translate_dakuten_equivalent_char(kana_char):
    dakuten_mapping = {
        "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
        "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
        "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
        "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
        "タ": "ダ", "チ": "ヂ", "ツ": "ヅ", "テ": "デ", "ト": "ド",
        "カ": "ガ", "キ": "ギ", "ク": "グ", "ケ": "ゲ", "コ": "ゴ",
        "サ": "ザ", "シ": "ジ", "ス": "ズ", "セ": "ゼ", "ソ": "ゾ",
        "ハ": "バ", "ヒ": "ビ", "フ": "ブ", "ヘ": "ベ", "ホ": "ボ"
    }

    dakuten_equiv = ""
    if kana_char in dakuten_mapping:
        dakuten_equiv = dakuten_mapping[kana_char]

    return dakuten_equiv


def translate_dakuten_equivalent(kana_char):
    """
    translate hiragana and katakana character to their dakuten equivalent
    e.g:
        ヒ: ビ
        く: ぐ
        み: ""
    :param kana_char: unicode kana char
    :return: dakuten equivalent if it exists otherwise empty string
    """
    return _translate_dakuten_equivalent_char(kana_char)


def translate_kana_iteration_mark(kana):
    """
    translate hiragana and katakana iteration marks: ゝ, ゞ, ヽ, ヾ
    e.g:
        こゝ: koko
        タヾ: tada
        かゞみち: kagaみち
    :param kana: unicode consisting of kana chars
    :return: unicode with kana iteration marks translated
    """
    prev_char = ""
    partial_kana = kana
    for c in kana:
        if c == hiragana_iter_mark or c == katakana_iter_mark:
            partial_kana = prev_char.join(partial_kana.split(c, 1))
        elif c == hiragana_voiced_iter_mark or c == katakana_voiced_iter_mark:
            partial_kana = translate_dakuten_equivalent(prev_char).join(partial_kana.split(c, 1))
        else:
            prev_char = c
    return partial_kana


def kanji_to_romaji(kana):
    if type(kana) == str:
        kana = kana
    pk = translate_kana_iteration_mark(kana)
    pk = translate_soukon_ch(pk)
    pk_list = prep_kanji(pk)
    translate_particles(pk_list)
    pk = translate_kanji(pk_list)
    pk = translate_to_romaji(pk)
    pk = translate_soukon(pk)
    r = translate_long_vowel(pk)
    return r.replace("\\\\", "\\").encode("unicode_escape")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(kanji_to_romaji(("".join(sys.argv[1:])).decode('unicode-escape')))
    else:
        print("Missing Kanji/Kana character argument\n" \
              "e.g: kanji_to_romaji.py \\u30D2")
