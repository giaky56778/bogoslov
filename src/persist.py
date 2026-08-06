from torch import float16
from sentence_transformers import SentenceTransformer

from db import session_scope
from model import Verse, Ngram, Embedding

strans_models = None


def get_sources() -> list[str]:
    with session_scope() as s:
        return list(s[0] for s in s.query(Verse.path).group_by(Verse.path).all())


def get_verse_text(path, filename, address) -> str:
    with session_scope() as s:
        result = (
            s.query(Verse.text)
            .filter(Verse.path == path)
            .filter(Verse.filename == filename)
            .filter(Verse.address == address)
            .first()
        )
        return result[0] if result else ""


def get_texts(sources: list[str] | None = None) -> list[tuple[str, str, str, str]]:
    with session_scope() as s:

        q = s.query(Verse)
        if sources:
            q = q.filter(Verse.path.in_(sources))
        result = q.all()
        return [(str(r.path), str(r.filename), str(r.address), str(r.text)) for r in result]


def find_regex(
    pattern: str, operator: str, sources: list[str] | None = None
) -> list[tuple[str, str, str]]:
    # TODO: Extract match position in regex to allow for the calculation of accuracy
    with session_scope() as s:
        q = s.query(Verse).filter(Verse.text.op(operator, is_comparison=True)(pattern))
        if sources:
            q = q.filter(Verse.path.in_(sources))
        result = q.all()

        return [(str(r.path), str(r.filename), str(r.address)) for r in result]


def find_ngram(
    n: int,
    lngram: str,
    estart: int,
    eend: int,
    etext: str,
    sources: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    with session_scope() as s:
        q = (
            s.query(Ngram, Verse)
            .filter(Ngram.n == n, Ngram.lemmas == lngram)
            .filter(Ngram.verse_id == Verse.id)
        )
        if sources:
            q = q.filter(Verse.path.in_(sources))
        result = q.all()
        return [(r[1].path, r[1].filename, r[1].address) for r in result]


def get_lemmas(verse_text: str) -> list[str]:
    with session_scope() as s:
        q = (
            s.query(Ngram.text)
            .join(Verse, Ngram.verse_id == Verse.id)
            .filter(Ngram.n == 1, Verse.text == verse_text)
        )
        return [str(res) for res in q.order_by(Ngram.pos.asc()).all()]


def get_strans_models() -> list[str]:
    with session_scope() as s:

        if "available_models" not in globals():
            global available_models
            available_models = [  # type: ignore
                r.model for r in s.query(Embedding.model).group_by(Embedding.model).all()
            ]

        return available_models  # type: ignore


def find_embeddings(
    model_name: str,
    text: str,
    sim_threshold: float = 0.8,
    sources: list[str] | None = None,
) -> list[tuple[str, str, str, str, float]]:
    with session_scope() as s:
        # Done so in order to release memory ASAP
        quote = SentenceTransformer(
            model_name, device="cpu", model_kwargs={"dtype": float16}
        ).encode(text)
        import gc

        gc.collect()

        q = (
            s.query(Embedding, Verse, Embedding.vector.cosine_distance(quote))
            .filter(Embedding.model == model_name)
            .filter(Embedding.verse_id == Verse.id)
            .filter(Embedding.vector.cosine_distance(quote) <= 1 - sim_threshold)
        )
        if sources:
            q = q.filter(Verse.path.in_(sources))
        result = q.all()

        return [
            (
                str(r[1].text),
                str(r[1].path),
                str(r[1].filename),
                str(r[1].address),
                1 - r[2],
            )
            for r in result
    ]


# result = find_embeddings(
#     "uaritm/multilingual_en_uk_pl_ru", "Блаженъ мѫжъ иже не иде на съвѣть нечъстивъїхъ"
# )
# print(result)
