#!/usr/bin/env python3

"""BogoSlov Populate

Schema needs to be preloaded.

Usage:
    populate.py [--historical] [-f | --force]
    populate.py [-v | --verses] [-n | --ngrams] [-e | --embeddings] [-f | --force]
    populate.py [--historical] [-v | --verses] [-n | --ngrams] [-e | --embeddings] [-f | --force]
    populate.py [-v | --verses] [-n | --ngrams] [--embedding=<name>] [-f | --force]
    
    populate.py (-h | --help)
    populate.py --version

Options:
    -h --help            Show this screen.
    --version            Show version.
    -v --verses          Generate index for Verses.
    -n --ngrams          Generate index for Ngrams (requires index for Verses).
    -e --embeddings      Generate index for Embeddings (requires index for Verses).
    --embedding=<name>   Generate index for Embeddings only for model <name> (requires index for Verses).
    -t --historical      Generate historical texts and highlight data.
    -f --force           Force regeneration even if it exists already.

"""

from lxml import etree  # type: ignore
from glob import glob
from pathlib import Path
import random

from tqdm import tqdm  # type: ignore
from docopt import docopt  # type: ignore
from sentence_transformers import SentenceTransformer
from sqlalchemy import delete, func  # type: ignore
from psycopg2.extras import NumericRange

from model import *

from settings import ns, unit, strans_models as models, ng_min, ng_max
from db import engine, Session, Base

from tei_converter import convert_tei, calculate_chapter_index

src = "/corpora/*/*.tei.xml"


def persist_verse(s: Session, fname: str):  # type: ignore
    print(fname)
    corpus = fname.split("/")[-2]
    ch = fname.split("/")[-1]
    root = etree.parse(fname)
    result = root.xpath(f"//tei:{unit}", namespaces=ns)
    data = []
    for e in tqdm(result):
        eid = e.get("id")
        tcontents = e.xpath(
            f"""//tei:{unit}[@id='{eid}']//tei:w/text()""", namespaces=ns
        )
        lcontents = e.xpath(
            f"""//tei:{unit}[@id='{eid}']//tei:w/@lemma""", namespaces=ns
        )
        if not tcontents or (len(tcontents) == 1 and not tcontents[0].strip()):
            continue
        data += [
            Verse(
                path=corpus,
                filename=ch,
                address=eid,
                text=" ".join(tcontents),
                lemmas=",".join(lcontents),
            )
        ]
    s.add_all(data)  # type: ignore
    s.commit()  # type: ignore


def persist_ngram(s, verse: str, n: int):
    tokens = [tex for tex in v.text.split(" ") if tex]
    lemmas = [lem for lem in v.lemmas.split(",") if lem]
    ngrams = []
    for i in range(len(lemmas) - n + 1):
        # TODO: handle better lemmatization mismatches
        if len(tokens) >= i + n:
            text = " ".join(tokens[i : i + n])
        elif len(tokens) > i:
            text = " ".join(tokens[i:])
        else:
            text = ""
        ngrams += [
            Ngram(
                n=n,
                lemmas=",".join(lemmas[i : i + n]),
                text=text,
                verse_id=v.id,
                pos=i,
            )
        ]
    s.add_all(ngrams)
    s.commit()


def persist_embedding(m: str, force=False):
    model = SentenceTransformer(m)
    vectors = []
    q = s.query(Verse)
    cnt = q.count()
    preexistent = s.query(Embedding).filter(Embedding.model == m).count()
    if cnt == preexistent and not force:
        print(f"Model {m} already loaded.")
        return
    if preexistent > 0:
        print(f"Cleaning up preloaded model {m}.")
        s.execute(delete(Embedding).where(Embedding.model == m))
    for v in tqdm(q.all(), total=cnt):
        primary = model.encode(v.text)
        vectors += [
            Embedding(
                model=m,
                vector=primary,
                verse_id=v.id,
            )
        ]
    s.add_all(vectors)
    s.commit()


if __name__ == "__main__":
    args = docopt(__doc__, version="BogoSlov Populate 1.0")
    # print(args)

    Base.metadata.create_all(engine)
    s = Session()

    if args["--verses"]:
        if args["--force"]:
            print("Cleaning up preloaded verses.")
            s.execute(delete(Embedding))
            s.execute(delete(Ngram))
            s.execute(delete(Verse))
        print("# Indexing Verses...")
        for fname in glob(src):
            persist_verse(s, fname)

    if args["--ngrams"]:
        files = list(
            s.query(Verse.path, Verse.filename)
            .group_by(Verse.path, Verse.filename)
            .all()
        )
        # print(files)
        if args["--force"]:
            print("Cleaning up preloaded N-grams.")
            s.execute(delete(Ngram))
        for path, filename in files:
            print(f"# Indexing N-grams: {path}/{filename}...")
            q = s.query(Verse).filter(Verse.path == path, Verse.filename == filename)
            for v in tqdm(q.all(), total=q.count()):
                for n in range(ng_min, ng_max + 1):
                    persist_ngram(s, v, n)

    if args["--embeddings"]:
        for m in models:
            print(f"# Indexing model: {m}...")
            persist_embedding(m, force=args["--force"])

    elif args["--embedding"]:
        m = args["--embedding"]
        if m not in models:
            print(f"Available models: {models}")
        else:
            print(f"# Indexing model: {m}...")
            try:
                persist_embedding(m, force=args["--force"])
            except ValueError as ve:
                print(repr(ve))

###
def persist_historical_texts(s, source_glob: str = src):
    for xml_path in glob(source_glob):
        path_obj = Path(xml_path)
        corpus_path = str(path_obj.parent)
        filename = path_obj.name.removesuffix(".tei.xml")

        text = convert_tei((corpus_path, filename))
        chapters = calculate_chapter_index(text)

        historical_text = HistoricalText(
                path=corpus_path.removeprefix('/corpora/'),
                filename=filename,
                text=text,
                chapters=chapters
            )
        s.add(historical_text)
        s.flush()
        j=0
        for value in text:
            if value['type']=='text' and value["text"]:
                s.add(
                    ConvertIndexHistorical(
                        textId              = historical_text.id,
                        lineRange           = value['id'],
                        lineIndex           = j,
                        wordIndexRange      = NumericRange(value["text"][0]["ID"],value["text"][-1]["ID"]+1)
                    )
                )
            j+=1

        biblical_text = BiblicalText(
            path=corpus_path.removeprefix('/corpora/'),
            filename=filename+" b",
            text=text,
            chapters=chapters
        )
        s.add(biblical_text)
        s.flush()
        j=0
        for value in text:
            if value['type']=='text' and value["text"]:
                s.add(
                    ConvertIndexBiblical(
                        textId              = biblical_text.id,
                        lineRange           = value['id'],
                        lineIndex           = j,
                        wordIndexRange      = NumericRange(value["text"][0]["ID"],value["text"][-1]["ID"]+1)
                    )
                )
            j+=1
        s.commit()
        print(f"Loaded {corpus_path}/{filename}")


def persist_highlight(s):

    def generate_non_overlapping_ranges(n: int, max_index: int) -> list[tuple[int, int]]:
        """Genera fino a n range disgiunti nel dominio [0, max_index)."""
        if n <= 0 or max_index <= 1:
            return []

        ranges: list[tuple[int, int]] = []
        current_pos = 0

        for _ in range(n):
            # Gap casuale prima del prossimo intervallo.
            current_pos += random.randint(0, 100)
            if current_pos >= max_index:
                break

            max_size = min(max(1, max_index // 12), max_index - current_pos)
            size = random.randint(1, max_size)
            end_pos = current_pos + size

            ranges.append((current_pos, end_pos))
            current_pos = end_pos

        return ranges

    #-------------------------------------

    # For colors
    for i in range(1, 6):
        color = HighlightColors(id=i)
        s.add(color)
    s.commit()

    # For highlight
    qH=s.query(
            HistoricalText.id,
            func.array_length(HistoricalText.text, 1).label("max_index")
        ).all()
    qB=s.query(
            BiblicalText.id,
            func.array_length(BiblicalText.text, 1).label("max_index")
        ).all()

    for h_text in qH:
        h_convert_idx = s.query(ConvertIndexHistorical).filter(
            ConvertIndexHistorical.textId == h_text.id
        ).all()

        for b_text in qB:
            b_convert_idx = s.query(ConvertIndexBiblical).filter(
                ConvertIndexBiblical.textId == b_text.id
            ).all()

            num_highlights = random.randint(0, 10)
            if num_highlights == 0:
                continue

            left_ranges  = generate_non_overlapping_ranges(num_highlights, h_text.max_index)
            right_ranges = generate_non_overlapping_ranges(num_highlights, b_text.max_index)

            for i in range(min(len(left_ranges), len(right_ranges))):
                hist_lower = left_ranges[i][0]
                bibl_lower = right_ranges[i][0]

                hist_start = next(
                    (e.id for e in h_convert_idx if hist_lower in e.wordIndexRange),
                    None
                )
                bibl_start = next(
                    (e.id for e in b_convert_idx if bibl_lower in e.wordIndexRange),
                    None
                )

                if hist_start is None or bibl_start is None:
                    continue

                highlight = TextHighlights(
                    color_id              = random.randint(1, random.randint(1, 5)),
                    historical_text_id    = h_text.id,
                    biblical_text_id      = b_text.id,
                    historical_range_word = NumericRange(left_ranges[i][0], left_ranges[i][1]),
                    biblical_range_word   = NumericRange(right_ranges[i][0], right_ranges[i][1]),
                    historical_start_line = hist_start,
                    biblical_start_line   = bibl_start,
                )
                s.add(highlight)

    s.commit()



if __name__ == "__main__":
    args = docopt(__doc__, version="BogoSlov Populate 1.0")
    # print(args)

    Base.metadata.create_all(engine)
    s = Session()

    if args["--historical"]:
        if args["--force"]:
            print("Cleaning up preloaded historical texts.")
            s.execute(delete(TextHighlights))
            s.execute(delete(ConvertIndexBiblical))
            s.execute(delete(ConvertIndexHistorical))
            s.execute(delete(HighlightColors))
            s.execute(delete(BiblicalText))
            s.execute(delete(HistoricalText))

        print("# Loading Historical Texts...")
        persist_historical_texts(s, src)
        persist_highlight(s)


    if args["--verses"]:
        if args["--force"]:
            print("Cleaning up preloaded verses.")
            s.execute(delete(Embedding))
            s.execute(delete(Ngram))
            s.execute(delete(Verse))
        print("# Indexing Verses...")
        for fname in glob(src):
            persist_verse(s, fname)

    if args["--ngrams"]:
        files = list(
            s.query(Verse.path, Verse.filename)
            .group_by(Verse.path, Verse.filename)
            .all()
        )
        # print(files)
        if args["--force"]:
            print("Cleaning up preloaded N-grams.")
            s.execute(delete(Ngram))
        for path, filename in files:
            print(f"# Indexing N-grams: {path}/{filename}...")
            q = s.query(Verse).filter(Verse.path == path, Verse.filename == filename)
            for v in tqdm(q.all(), total=q.count()):
                for n in range(ng_min, ng_max + 1):
                    persist_ngram(s, v, n)

    if args["--embeddings"]:
        for m in models:
            print(f"# Indexing model: {m}...")
            persist_embedding(m, force=args["--force"])

    elif args["--embedding"]:
        m = args["--embedding"]
        if m not in models:
            print(f"Available models: {models}")
        else:
            print(f"# Indexing model: {m}...")
            try:
                persist_embedding(m, force=args["--force"])
            except ValueError as ve:
                print(repr(ve))

