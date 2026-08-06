from sqlalchemy import select

from db import session_scope
from model import *

def get_biblical_line_index_by_word(path: str, filename: str, word_id: int) -> int | None:
    with session_scope() as s:
        stmt = (
            select(ConvertIndexBiblical.lineIndex)
            .join(BiblicalText, ConvertIndexBiblical.textId == BiblicalText.id)
            .where(
                BiblicalText.path == path,
                BiblicalText.filename == filename,
                ConvertIndexBiblical.wordIndexRange.contains(word_id),
            )
        )
        result = s.execute(stmt).scalar()
        return result

