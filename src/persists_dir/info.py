from sqlalchemy import select

from db import session_scope
from model import *

def get_historical_line_index_by_word(path: str, filename: str, word_id: int, user) -> int | None:
    with session_scope() as s:
        stmt = (
            select(ConvertIndexHistorical.lineIndex)
            .join(HistoricalText, ConvertIndexHistorical.textId == HistoricalText.id)
            .join(TextUser, HistoricalText.id == TextUser.text_id)
            .where(
                HistoricalText.path == path,
                HistoricalText.filename == filename,
                ConvertIndexHistorical.wordIndexRange.contains(word_id),
                User.id == user.id
            )
        )
        result = s.execute(stmt).scalar()
        if result is None:
            raise ValueError("Error: user cant access this text")
        
        return result

