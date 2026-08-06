from typing import Callable

import regex as re  # type: ignore
from functools import reduce
import operator
from lxml import etree  # type: ignore
from tqdm import tqdm  # type: ignore
from fuzzywuzzy import process  # type: ignore
import unicodedata

from tei_util import word_templ


def align_lemmas(words: list[str], lemmas: list[str]) -> list[str]:
    """
    Fuzzy-guesses how to make lemmas correspond to words.

    >>> words = ['рѹвімьсцѣмь', 'ѡсана', 'с҃нѹ', 'д҃въ', 'г҃лѫште', 'рѹвімьсцѣмь', 'б҃лгнъ', 'грѧдѧі', 'въ', 'імѧ', 'г҃не', 'б҃лгнъ', 'грѧдѧі', 'б҃ъ', 'отъ']
    >>> lemmas = ['рѹвімьсцѣти', 'ѡсана', 'сꙑнъ', 'давꙑдовъ', 'глаголати', 'и', 'рѹвімьсцѣти', 'благословлѥнъ', 'грѧсти', 'въ', 'имѧ', 'господьнь', 'благословлѥнъ', 'грѧсти', 'богъ', 'отъ']
    >>> align_lemmas(words, lemmas)
    ['рѹвімьсцѣти', 'ѡсана', 'сꙑнъ', 'давꙑдовъ', 'глаголати', 'рѹвімьсцѣти', 'благословлѥнъ', 'грѧсти', 'въ', 'имѧ', 'господьнь', 'благословлѥнъ', 'грѧсти', 'богъ', 'отъ']
    """
    # assert len(words) > len(lemmas), f"Expected more words than lemmas, but opposite:\nwords={len(words)}\nlemmas({len(lemmas)})"
    # lw = [len(w) for w in words]
    # ll = [len(w) for w in lemmas]
    # result = [(fuzzywuzzy.extractOne(w, lemmas) if len(w) > 5 else "") for w in words]
    result = []
    for i, w in enumerate(words):
        # abbreviations taken by first letter
        if w and len(w) > 1 and ord(w[1]) in [1155, 1159]:  # ['◌҃', '◌҇']
            # print(f"tidlo at {i}")
            # print(f"len:{len(words)},front:{i},back:{i-len(words)}")
            if w[0] == lemmas[i][0]:
                result += [lemmas[i]]
            elif w[0] == lemmas[i - len(words)][0]:
                result += [lemmas[i - len(words)]]
            else:
                # Unable to identify
                result += [""]
        else:
            # Limit search to vicinity of position
            eps = 3
            focus = lemmas
            if i - len(words) + eps < 0:
                focus = focus[: i - len(words) + eps]
            if i - eps > 0:
                focus = focus[i - eps :]
            result += [process.extractOne(w, focus)[0]]
    return result


def get_word_ranges(fulltext: str, ltext: str) -> list[tuple[str, int, int, str]]:
    """
    Returns list of lemmas, the corresponding indices in the original text, and the original word.


    >>> get_word_ranges("Hello, this is me", "hello this is me")
    [('hello', 0, 5, 'Hello'), ('this', 7, 11, 'this'), ('is', 12, 14, 'is'), ('me', 15, 17, 'me')]
    >>> get_word_ranges("Here goes nothing!", "here go nothing")
    [('here', 0, 4, 'Here'), ('go', 5, 9, 'goes'), ('nothing', 10, 17, 'nothing')]
    >>> get_word_ranges("стати и на", "стати и на")
    [('стати', 0, 5, 'стати'), ('и', 6, 7, 'и'), ('на', 8, 10, 'на')]

    >>> xml ='''<lg xmlns="http://www.tei-c.org/ns/1.0" id="1_2" n="2"><cl id="1_2_1">И въ законѣ его поѹчитъ сѧ дънъ и нощъ ⁘</cl><cl id="1_2_2">И бѫдетъ ꙗко дрѣво сажденое при исходищихъ водамъ  ⁘</cl></lg>'''
    >>> lemmas = 'и въ законъ и поучити себе дънъ и нощь и бꙑти ꙗко дрѣво садити при исходище вода'
    >>> get_word_ranges(xml, lemmas)
    [('и', 70, 71, 'И'), ('въ', 72, 74, 'въ'), ('законъ', 75, 81, 'законѣ'), ('и', 82, 85, 'его'), ('поучити', 86, 93, 'поѹчитъ'), ('себе', 94, 96, 'сѧ'), ('дънъ', 97, 101, 'дънъ'), ('и', 102, 103, 'и'), ('нощь', 104, 108, 'нощъ'), ('и', 130, 131, 'И'), ('бꙑти', 132, 138, 'бѫдетъ'), ('ꙗко', 139, 142, 'ꙗко'), ('дрѣво', 143, 148, 'дрѣво'), ('садити', 149, 157, 'сажденое'), ('при', 158, 161, 'при'), ('исходище', 162, 172, 'исходищихъ'), ('вода', 173, 179, 'водамъ')]

    >>> ft = "рѹвімьсцѣмь • ѡсана с҃нѹ д҃въ г҃лѫште •  рѹвімьсцѣмь б҃лгнъ грѧдѧі въ імѧ г҃не • б҃лгнъ грѧдѧі б҃ъ отъ"
    >>> lt = "рѹвімьсцѣти • ѡсана сꙑнъ давꙑдовъ глаголати и рѹвімьсцѣти благословлѥнъ грѧсти въ имѧ господьнь • благословлѥнъ грѧсти богъ отъ"
    >>> get_word_ranges(ft, lt)
    [('рѹвімьсцѣти', 0, 11, 'рѹвімьсцѣмь'), ('ѡсана', 14, 19, 'ѡсана'), ('сꙑнъ', 20, 24, 'с҃нѹ'), ('давꙑдовъ', 25, 29, 'д҃въ'), ('глаголати', 30, 37, 'г҃лѫште'), ('рѹвімьсцѣти', 41, 52, 'рѹвімьсцѣмь'), ('благословлѥнъ', 53, 59, 'б҃лгнъ'), ('грѧсти', 60, 66, 'грѧдѧі'), ('въ', 67, 69, 'въ'), ('имѧ', 70, 73, 'імѧ'), ('господьнь', 74, 78, 'г҃не'), ('благословлѥнъ', 81, 87, 'б҃лгнъ'), ('грѧсти', 88, 94, 'грѧдѧі'), ('богъ', 95, 98, 'б҃ъ'), ('отъ', 99, 102, 'отъ')]
    """
    lltokens = [
        [e for e in re.split(r"\W+", s) if e]
        for s in re.split(r"<.+?>+", fulltext)
        if s
    ]
    # print(lltokens)
    ttokens = reduce(operator.concat, lltokens)  # type: ignore
    ltokens = [e for e in re.split(r"\W+", ltext) if e]
    # Sometimes the match result is inaccurate, typically when abbreviations present
    if len(ttokens) != len(ltokens):
        ltokens = align_lemmas(ttokens, ltokens)
    result = []
    spos = 0
    epos = 0
    for i, lemma in enumerate(ltokens):
        spos = epos + fulltext[epos:].find(ttokens[i])
        epos = spos + fulltext[spos:].find(ttokens[i]) + len(ttokens[i])
        result += [(lemma, spos, epos, fulltext[spos:epos])]
    return result


def get_ngrams(
    fulltext: str, ltext: str, n: int = 3
) -> dict[tuple[str, ...], list[tuple[int, int, str]]]:
    word_ranges = get_word_ranges(fulltext, ltext)
    ltokens = [e for e in re.split(r"\W+", ltext) if e]
    span = []
    result: dict[tuple[str, ...], list[tuple[int, int, str]]] = {}
    for i, t in enumerate(ltokens):
        span += [t]
        if len(span) < n:
            continue
        ngram = tuple(span)
        if ngram not in result:
            result[ngram] = []
        spos = word_ranges[i - n + 1][1]
        epos = word_ranges[i - n + 1][2]  # was word_ranges[i][2]
        result[ngram] += [(spos, epos, fulltext[spos:epos])]
        # print(f"{i}/{spos} {i-n+1}/{epos}|{fulltext[spos:epos]}|{ttokens[i]}|{ttokens[i-n+1]}|{ngram}")
        span = span[1:]
    return result


def extract_text(node) -> str:
    return "".join(node.itertext()).strip()


def lemmatize_node(
    node, sentence_lemmatizer_func: Callable[[str], list[tuple[str, str]]]
) -> list[tuple[str, int, int, str, str]]:
    """
    Returns lemma, positions range, word and xml snippet in range
    >>> from lxml import etree
    >>> import re
    >>> node = etree.fromstring('''<lg id="1_1" n="1"><cl id="1_1_1">И на пѫти грьшънꙑхъ не ста .  </cl><cl id="1_1_2">И на сьдалищи гѹбителъ </cl><cl id="1_1_3">не сѣде .</cl><cl id="1_1_4">Нъ въ законѣ гдни волѣ его .</cl></lg>''')
    >>> lemmatize_node(node, lambda x: [(t, t) for t in re.split(r'\\W+', x) if t.strip()])
    [('И', 34, 35, 'И', 'И'), ('на', 36, 38, 'на', 'на'), ('пѫти', 39, 43, 'пѫти', 'пѫти'), ('грьшънꙑхъ', 44, 53, 'грьшънꙑхъ', 'грьшънꙑхъ'), ('не', 54, 56, 'не', 'не'), ('ста', 57, 60, 'ста', 'ста'), ('И', 84, 85, 'И', 'И'), ('на', 86, 88, 'на', 'на'), ('сьдалищи', 89, 97, 'сьдалищи', 'сьдалищи'), ('гѹбителъ', 98, 106, 'гѹбителъ', 'гѹбителъ'), ('не', 127, 129, 'не', 'не'), ('сѣде', 130, 134, 'сѣде', 'сѣде'), ('Нъ', 156, 158, 'Нъ', 'Нъ'), ('въ', 159, 161, 'въ', 'въ'), ('законѣ', 162, 168, 'законѣ', 'законѣ'), ('гдни', 169, 173, 'гдни', 'гдни'), ('волѣ', 174, 178, 'волѣ', 'волѣ'), ('его', 179, 182, 'его', 'его')]
    """
    xml = etree.tostring(node, encoding="unicode")
    text = extract_text(node)
    pairs = sentence_lemmatizer_func(text)
    ranges = [
        (l, s, e, w, xml[s:e])
        for (l, s, e, w) in get_word_ranges(
            xml, " ".join(p[1] for p in pairs if p[0].isalpha())
        )
    ]
    return ranges


def lemmatize_xml(
    fname: str, sentence_lemmatizer_func: Callable[[str], list[tuple[str, str]]]
) -> str:
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    ns_def = f''' xmlns="{ns["tei"]}"'''
    root = etree.parse(fname, parser=etree.XMLParser())
    ranges = []
    xml = etree.tostring(root, encoding="unicode")
    for verse_id in tqdm(root.xpath("//tei:lg/@id", namespaces=ns)):  # type: ignore
        # print(verse_id)
        node = root.xpath(f"//tei:lg[@id='{verse_id}']", namespaces=ns)[0]  # type: ignore
        try:
            subxml = etree.tostring(node, encoding="unicode")  # type: ignore
            subxml = subxml.replace(ns_def, "")  # type: ignore
            # print(xml)
            # print(subxml)
            offset = xml.find(subxml) - len(ns_def)
            # print(offset)
            lranges = lemmatize_node(node, sentence_lemmatizer_func)
            newranges = [
                (
                    r[0],
                    r[1] + offset,
                    r[2] + offset,
                    r[3],
                    r[4],
                    xml[r[1] + offset : r[2] + offset],
                )
                for r in lranges
            ]
            ranges += newranges
            # print("verse", offset, newranges)
        except AssertionError:
            # print(verse_id)
            for line_id in root.xpath(
                f"//tei:lg[@id='{verse_id}']/tei:cl/@id", namespaces=ns
            ):
                # print(line_id)
                node2 = root.xpath(f"//tei:lg/tei:cl[@id='{line_id}']", namespaces=ns)[
                    0
                ]
                subxml = etree.tostring(node2, encoding="unicode")
                subxml = subxml.replace(ns_def, "")
                try:
                    offset = xml.find(subxml) - len(ns_def)
                    llranges = lemmatize_node(node2, sentence_lemmatizer_func)
                    newranges = [
                        (
                            r[0],
                            r[1] + offset,
                            r[2] + offset,
                            r[3],
                            r[4],
                            xml[r[1] + offset : r[2] + offset],
                        )
                        for r in llranges
                    ]
                    ranges += newranges
                    # print("line", offset, newranges)
                except AssertionError:
                    offset = xml.find(subxml)
                    spos = subxml.find(">") + 1
                    epos = subxml.rfind("<")
                    newranges = [
                        (
                            " ".join(
                                p[1]
                                for p in sentence_lemmatizer_func(subxml[spos:epos])
                            ),
                            spos + offset,
                            epos + offset,
                            xml[spos + offset : epos + offset],
                        )  # type: ignore
                    ]
                    ranges += newranges
                    # print("multiword", offset, newranges)
    # return ranges
    for i, r in enumerate(reversed(ranges)):
        assert not any(
            char in r[0] for char in "<>"
        ), f"Lemma {r[0]} for word {xml[r[1] : r[2]]} contains non-compliant characters"
        ri = len(ranges) - i
        xml = (
            xml[: r[1]]
            + word_templ.format(
                pos=f"{verse_id}__{ri}", lemma=r[0], word=xml[r[1] : r[2]]
            )
            + xml[r[2] :]
        )
        # print(xml)
    return xml


def link2fname(link: str):
    """
    >>> link2fname('<a href="http://157.180.18.192:8780/results/lcs-BMSZ-ac3cb180f466a148f5a17264d531c0ba.xlsx">[Export Results]</a>')
    'lcs-BMSZ-ac3cb180f466a148f5a17264d531c0ba.xlsx'
    """
    fname = link.split('"')[1].split("/")[-1]
    return fname

###

def merge_hybrid_raw(
    k: int | None,
    algo: str,
    raw: list[tuple[str, str, float]],
    texts: dict,
    scores: dict,
    problematic: bool = False
):
    rank_k = k or 60
    raw_sorted = sorted(raw, key=lambda t: float(t[2]), reverse=True)

    for i, (text, addr, _) in enumerate(raw_sorted):
        if not problematic:
            if addr not in texts:  # addr not in scores: it's useless, if text is false then scores is false
                texts[addr] = text
                scores[addr] = {
                    "score": 0.0,
                    "algos": []
                }

            scores[addr]["score"] += 1 / ((i + 1) + rank_k)  # type: ignore
            scores[addr]["algos"].append(algo)
        elif addr.split("$$")[0] in texts and text == texts[addr]:
            scores[addr]["score"] += 1 / ((i + 1) + rank_k)  # type: ignore
            scores[addr]["algos"].append(algo)
        else:
            addrPlus = addr + "$$" + algo + "_" + str(i)
            texts[addrPlus] = text
            scores[addrPlus] = {
                "score": 1 / ((i + 1) + rank_k),
                "algos": [algo]
            }

def compose_grouped_text(q):
    temp=dict()
    for r in q:
        temp.setdefault(r.path, []).append({
            "id": int(r.id),
            "filename": str(r.filename)
        })
    
    
    result = []
    for value in temp.keys():
        result.append({
            "path":value,
            "items":temp[value]
        })
        
    return result

def strip_punctuation(word: str) -> str:
    return "".join(ch for ch in word if not unicodedata.category(ch).startswith("P"))

def parse_urn(urn_h: str) -> tuple[str, str]:
    urn_h = urn_h.split(":", 1)[0]
    parts = urn_h.split(".")
    path_h = ".".join(parts[:-1])
    filename_h = parts[-1]
    return path_h, filename_h


if __name__ == "__main__":
    # src = "sample-tei.xml"
    # src = "sample-multiword-tei.xml"
    # src = "sample-verse-tei.xml"
    src = "sample-line-tei.xml"
    src = "sample-new-tei.xml"
    # src = "Bologna Psalter/BM1.tei.xml"
    func = lambda x: [(t, t) for t in re.split(r"\\W+", x) if t.strip()]
    result = lemmatize_xml(src, func)
    print(result)
