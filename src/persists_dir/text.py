from psycopg2.extras import NumericRange
from sqlalchemy import func, select

from settings import LINE_EXTRACT_UPPER,LINE_EXTRACT_LOWER
from db import session_scope
from model import *
from schemas import *
from tei_converter import calculate_chapter_index
from util import compose_grouped_text

def get_full_text_by_tables(
    text_model,
    index_model,
    query: TextQuery
) -> tuple[dict, dict | None, dict, int]:
    with session_scope() as s:
        id = query.text_id
        path = query.path
        filename = query.filename

        if filename is not None and path is not None:
            qR = s.execute(
                select(text_model.id)
                .where(
                    text_model.path == path,
                    text_model.filename == filename
                )
            ).scalar()

            if qR is None:
                raise ValueError("Testo non trovato")
            id = int(qR)

        q = select(text_model.text, text_model.chapters).where(text_model.id == id)
        res = s.execute(q).first()
        if res is None:
            raise ValueError("Testo non trovato")
        text, chapters = res

        rows_index_q = s.execute(
            select(index_model.lineIndex, index_model.wordIndexRange)
            .where(index_model.textId == id)
        ).all()
        max_index = s.execute(
            select(func.max(index_model.lineIndex))
            .where(index_model.textId == id)
        ).scalar() or 0

        if chapters is None:
            raise ValueError('Non esiste il testo selezionato')

        result_index = {
            "content": {
                r.lineIndex: {"start": r.wordIndexRange.lower, "end": r.wordIndexRange.upper}
                for r in rows_index_q
            },
            "maxIndex": max_index
        }

        return text, chapters, result_index, id  # type: ignore

def get_portion_text_by_tables(
    text_model,
    index_model,
    query: TextPortionQuery
) -> tuple[dict, dict | None, dict, int]:
    with session_scope() as s:
        id = query.text_id
        line = query.line
        lineNumber = query.lineNumber
        wordId = query.wordId
        path = query.path
        filename = query.filename

        if filename is not None and path is not None:
            qR = s.execute(
                select(text_model.id)
                .where(
                    text_model.path == path,
                    text_model.filename == filename
                )
            ).scalar()

            if qR is None:
                raise ValueError("Testo non trovato")
            id = int(qR)

        if lineNumber is not None:
            spl = lineNumber.split(".")
            qT = (
                select(func.min(index_model.lineIndex))
                .where(index_model.textId == id)
            )

            if len(spl) == 2:
                qT = qT.where(index_model.lineRange.like(
                    "\\_".join(spl) + "\\_%", escape="\\"
                ))
            elif len(spl) == 3:
                qT = qT.where(index_model.lineRange == "_".join(spl))
            else:
                raise ValueError("Formato non disponibile")

            line = s.execute(qT).scalar()
            if line is None:
                raise ValueError('Non esiste il testo selezionato')

        if wordId is not None:
            qR = s.execute(
                select(index_model.lineIndex)
                .where(
                    index_model.textId == id,
                    index_model.wordIndexRange.contains(wordId)
                )
            ).scalar()
            if qR is None:
                raise ValueError('Non esiste il testo selezionato')
            line = int(qR)

        if line is None:
            raise ValueError('Non esiste il testo selezionato')

        q = select(
            text_model.text[line + 1 - LINE_EXTRACT_LOWER : line + 1 + LINE_EXTRACT_UPPER],
            text_model.chapters
        ).where(text_model.id == id)
        res = s.execute(q).first()
        if res is None:
            raise ValueError('Non esiste il testo selezionato')
        text, chapters = res

        rows_index_q = s.execute(
            select(index_model.lineIndex, index_model.wordIndexRange)
            .where(
                index_model.textId == id,
                index_model.lineIndex >= line - LINE_EXTRACT_LOWER,
                index_model.lineIndex <= line + LINE_EXTRACT_UPPER,
            )
        ).all()
        max_index = s.execute(
            select(func.max(index_model.lineIndex))
            .where(
                index_model.textId == id,
                index_model.lineIndex >= line - LINE_EXTRACT_LOWER,
                index_model.lineIndex <= line + LINE_EXTRACT_UPPER,
            )
        ).scalar() or 0

        if chapters is None or not rows_index_q:
            raise ValueError('Non esiste il testo selezionato')

        chapter = None
        for c in chapters:
            if c["indexMin"] <= int(line) <= c["indexMax"]:
                chapter = c
                break

        result_index = {
            "content": {
                r.lineIndex: {"start": r.wordIndexRange.lower, "end": r.wordIndexRange.upper}
                for r in rows_index_q
            },
            "maxIndex": max_index
        }

        return text, chapter, result_index, id  # type: ignore

def get_text_name_by_table(table):
    with session_scope() as s:
        rows = s.execute(select(table.id, table.filename, table.path)).all()
        return compose_grouped_text(rows)

def biblical_text_exists(path: str, filename: str) -> bool:
    with session_scope() as s:
        return s.execute(
            select(BiblicalText.id).where(
                BiblicalText.path == path,
                BiblicalText.filename == filename,
            )
        ).first() is not None

def persist_biblical_text(path: str, filename: str, text: list[dict]) -> int:
    with session_scope() as s:
        biblical_text = BiblicalText(
            path=path,
            filename=filename,
            text=text,
            chapters=calculate_chapter_index(text),
        )
        s.add(biblical_text)
        s.flush()

        for line_index, value in enumerate(text):
            if value["type"] == "text" and value["text"]:
                s.add(
                    ConvertIndexBiblical(
                        textId=biblical_text.id,
                        lineRange=value["id"],
                        lineIndex=line_index,
                        wordIndexRange=NumericRange(value["text"][0]["ID"], value["text"][-1]["ID"] + 1),
                    )
                )

        s.commit()
        s.refresh(biblical_text)
        return biblical_text.id

def delete_text(id: int):
    with session_scope() as s:
        stmt = select(BiblicalText).where(BiblicalText.id == id)
        deleteMe = s.scalar(stmt)
        if deleteMe is None:
            raise ValueError("Testo non trovato")

        s.delete(deleteMe)
        s.commit()
