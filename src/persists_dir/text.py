from psycopg2.extras import NumericRange
from sqlalchemy import func, select, and_, or_
from typing import Type

from settings import LINE_EXTRACT_UPPER,LINE_EXTRACT_LOWER
from db import session_scope
from model import *
from schemas import *
from tei_converter import calculate_chapter_index
from util import compose_grouped_text


def get_full_text_by_tables(
    text_model: Type[BiblicalText] | Type[HistoricalText],
    index_model: Type[ConvertIndexBiblical] | Type[ConvertIndexHistorical],
    query: TextQuery,
    user = None
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
                raise ValueError("Error: text not found")
            id = int(qR)

        if user is not None and user.id is not None:
            owner_check = s.execute(
                select(TextUser.id)
                .where(
                    TextUser.text_id == id, 
                    TextUser.user_id == user.id
                )
            ).first()
            if not owner_check:
                raise ValueError("Error: text not found or user cant access this text")

        q = select(text_model.text, text_model.chapters).where(text_model.id == id)
        res = s.execute(q).first()
        if res is None:
            raise ValueError("Error: text not found")
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
            raise ValueError('Error: text not found')

        result_index = {
            "content": {
                r.lineIndex: {"start": r.wordIndexRange.lower, "end": r.wordIndexRange.upper}
                for r in rows_index_q
            },
            "maxIndex": max_index
        }

        if id is None:
            raise ValueError("Error: text not found")

        return text, chapters, result_index, id

def get_portion_text_by_tables(
    text_model: Type[BiblicalText] | Type[HistoricalText],
    index_model: Type[ConvertIndexBiblical] | Type[ConvertIndexHistorical],
    query: TextPortionQuery,
    user = None
):
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
                raise ValueError("Error: text not found")
            id = int(qR)

        if user is not None and user.id is not None:
            owner_check = s.execute(
                select(TextUser.id)
                .where(TextUser.text_id == id, TextUser.user_id == user.id)
            ).first()
            if not owner_check:
                raise PermissionError("Permission denied: user cant caccess this text")

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
                raise ValueError("Error: lineNumber format is wrong")

            line = s.execute(qT).scalar()
            if line is None:
                raise ValueError("Error: text not found")

        if wordId is not None:
            qR = s.execute(
                select(index_model.lineIndex)
                .where(
                    index_model.textId == id,
                    index_model.wordIndexRange.contains(wordId)
                )
            ).scalar()
            if qR is None:
                raise ValueError("Error: text not found")
            line = int(qR)

        if line is None:
            raise ValueError("Error: text not found")

        q = select(
            text_model.text[line + 1 - LINE_EXTRACT_LOWER : line + 1 + LINE_EXTRACT_UPPER],
            text_model.chapters
        ).where(text_model.id == id)
        res = s.execute(q).first()
        if res is None:
            raise ValueError("Error: text not found")
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
            raise ValueError("Error: text not found")

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

        tempLine= line - LINE_EXTRACT_LOWER
        startLine= tempLine if tempLine >0 else 0
        return text, chapter, result_index, id, startLine

def get_text_name_by_table(table: Type[BiblicalText] | Type[HistoricalText], user=None):
    with session_scope() as s:
        stmt = select(table.id, table.filename, table.path)
        if user is not None and user.id is not None:
            stmt = stmt.join(TextUser, TextUser.text_id == table.id).where(TextUser.user_id == user.id)
        rows = s.execute(stmt).all()
        return compose_grouped_text(rows)

def historical_text_exists(path: str, filename: str, s) -> bool:
    return s.execute(
        select(HistoricalText.id).where(
            HistoricalText.path == path,
            HistoricalText.filename == filename,
        )
    ).first() is not None

def persist_historical_text(path: str, filename: str, text: list[dict], s, hashText: str | None = None) -> int:
    historical_text = HistoricalText(
        path=path,
        filename=filename,
        text=text,
        chapters=calculate_chapter_index(text),
        hashText=hashText,
    )
    s.add(historical_text)
    s.flush()

    for line_index, value in enumerate(text):
        if value["type"] == "text" and value["text"]:
            s.add(
                ConvertIndexHistorical(
                    textId=historical_text.id,
                    lineRange=value["id"],
                    lineIndex=line_index,
                    wordIndexRange=NumericRange(value["text"][0]["ID"], value["text"][-1]["ID"] + 1),
                )
            )

    s.flush()
    s.refresh(historical_text)
    return historical_text.id

def delete_text_for_user(id: int, user, s):
    stmt_text = select(HistoricalText).where(HistoricalText.id == id)
    text_obj = s.scalar(stmt_text)
    if text_obj is None:
        raise ValueError("Error: text not found")

    stmt_user = select(TextUser).where(TextUser.text_id == id, TextUser.user_id == user.id)
    user_assoc = s.scalar(stmt_user)
    if user_assoc is None:
        raise PermissionError("Permission denide: user cant acess this text")

    stmt_count = select(func.count(TextUser.id)).where(TextUser.text_id == id)
    owner_count = s.scalar(stmt_count)

    if owner_count > 1:
        s.delete(user_assoc)
    else:
        s.delete(text_obj)
    
    s.flush()

def get_historical_text_by_hash(hashText: str, s) -> HistoricalText | None:
    stmt = select(HistoricalText).where(HistoricalText.hashText == hashText)
    return s.execute(stmt).scalar()

def persist_text_user(user, text_id: int, s):
    stmt = select(TextUser.id).where(
        TextUser.user_id == user.id,
        TextUser.text_id == text_id
    )
    if s.execute(stmt).first():
        raise ValueError("Error: text already exist for this user")

    q = TextUser(
        user_id= user.id, 
        text_id=text_id
    )
    s.add(q)
    s.flush()

def check_alredy_exist(path:str,filename:str,hashText:str) -> bool:
    with session_scope() as s:
        stmt = (
            select(HistoricalText.id)
            .where(
                or_(
                    and_(
                        HistoricalText.path == path, 
                        HistoricalText.filename == filename
                    ),
                    HistoricalText.hashText == hashText
                )
            )
        )
        return s.execute(stmt).first() is not None

def check_text_property(path:str,filename:str,user) -> bool:
    with session_scope() as s:
        q = s.execute(
            select(TextUser)
            .join(HistoricalText, HistoricalText.id == TextUser.text_id)
            .where(
                HistoricalText.filename==filename,
                HistoricalText.path==path,
                TextUser.user_id==user.id
            )
        ).scalar()
        return q is not None
