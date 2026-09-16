from psycopg2.extras import NumericRange
from sqlalchemy import func, select, exists, and_, or_

from settings import LINE_EXTRACT_UPPER,LINE_EXTRACT_LOWER
from db import session_scope
from model import *
from schemas import *
from util import parse_urn

def check_texts_exist(s, idH: int, idB: int):
    h_exists = bool(s.scalar(select(exists().where(BiblicalText.id == idB))))
    b_exists = bool(s.scalar(select(exists().where(HistoricalText.id == idH))))
    if not h_exists or not b_exists:
        raise ValueError("Testo non trovato")

def common_get_quotes(rows) -> dict:
    grouped = dict()
    if rows:
        for r in rows:
            grouped[r.id] = {
                "color": r.color_id,
                "historical": {"startWord": r.historical_range_word.lower, "endWord": r.historical_range_word.upper - 1},
                "biblical": {"startWord": r.biblical_range_word.lower, "endWord": r.biblical_range_word.upper - 1},
            }
    
    return grouped


def get_quotes(idH: int, idB: int, user) -> dict:
    with session_scope() as s:
        stmt = ( 
            select(TextHighlights)
            .join(TextUser, TextUser.id == TextHighlights.text_user_id)
            .where(
                TextUser.text_id == idH,
                TextHighlights.biblical_text_id == idB,
                TextUser.user_id == user.id,
            )
        )
        rows = s.scalars(stmt).all()
        grouped = common_get_quotes(rows)
        if not grouped:
            check_texts_exist(s, idH, idB)
        return grouped

def get_quotes_portion(idH: int, idB: int, lineB: int, lineH: int, user) -> dict:
    with session_scope() as s:
        stmt = (
            select(TextHighlights)
            .join(TextUser, TextUser.id == TextHighlights.text_user_id)
            .where(
                TextUser.text_id == idB,
                TextHighlights.biblical_text_id == idH,
                TextUser.user_id == user.id,
            )
            .join(ConvertIndexHistorical, ConvertIndexHistorical.id == TextHighlights.historical_start_line)
            .join(ConvertIndexBiblical, ConvertIndexBiblical.id == TextHighlights.biblical_start_line)
            .where(
                or_(
                    and_(
                        ConvertIndexHistorical.lineIndex >= lineB - LINE_EXTRACT_LOWER,
                        ConvertIndexHistorical.lineIndex <= lineB + LINE_EXTRACT_UPPER
                    ),
                    and_(
                        ConvertIndexBiblical.lineIndex >= lineH - LINE_EXTRACT_LOWER,
                        ConvertIndexBiblical.lineIndex <= lineH + LINE_EXTRACT_UPPER
                    )
                )
            )
        )
        rows = s.scalars(stmt).all()
        grouped = common_get_quotes(rows)
        if not grouped:
            check_texts_exist(s, idH, idB)
        return grouped

def update_quotes(
    id: int,
    toUpdate: HighlightUpdate,
    user
):
    with session_scope() as s:
        stmt = select(TextHighlights).where(TextHighlights.id == id)
        result = s.scalar(stmt)

        if result is None:
            raise ValueError("Highlight non trovato")
            
        user_assoc = s.execute(select(TextUser).where(TextUser.id == result.text_user_id)).scalar_one()
        if user_assoc.user_id != user.id:
            raise PermissionError("Utente non autorizzato a modificare questo highlight.")
        
        if toUpdate.color is not None:
            result.color_id = toUpdate.color
        if toUpdate.biblical is not None:
            biblical_start_line = s.execute(
                select(ConvertIndexBiblical.id)
                .where(
                    ConvertIndexBiblical.textId == result.biblical_text_id,
                    ConvertIndexBiblical.lineIndex == toUpdate.biblical.startLine,
                )
            ).scalar_one()
            result.biblical_range_word = NumericRange(toUpdate.biblical.startWord, toUpdate.biblical.endWord + 1)
            result.biblical_start_line = biblical_start_line
        if toUpdate.historical is not None:
            historical_start_line = s.execute(
                select(ConvertIndexHistorical.id)
                .join(TextUser, TextUser.id == result.text_user_id)
                .where(
                    ConvertIndexHistorical.textId == TextUser.text_id,
                    ConvertIndexHistorical.lineIndex == toUpdate.historical.startLine,
                )
            ).scalar_one()
            result.historical_range_word = NumericRange(toUpdate.historical.startWord, toUpdate.historical.endWord + 1)
            result.historical_start_line = historical_start_line

        s.commit()
        s.refresh(result)

def delete_highlight(id: int, user):
    with session_scope() as s:
        stmt = select(TextHighlights).where(TextHighlights.id == id)
        deleteMe = s.scalar(stmt)
        if deleteMe is None:
            raise ValueError("Highlight non trovato") 
            
        user_assoc = s.execute(select(TextUser).where(TextUser.id == deleteMe.text_user_id)).scalar_one()
        if user_assoc.user_id != user.id:
            raise PermissionError("Utente non autorizzato a eliminare questo highlight.")
        
        s.delete(deleteMe)
        s.commit()

def list_all_biblical_highlights(
    path: str,
    filename: str,
    user,
):
    with session_scope() as s:
        groups: dict[tuple[str, str], list] = {}

        qRes = s.execute(
            select(
                ConvertIndexHistorical.lineIndex.label("historical_start_line"),
                ConvertIndexBiblical.lineIndex.label("biblical_start_line"),
                TextHighlights.color_id,
                TextHighlights.historical_range_word,
                TextHighlights.biblical_range_word,
                BiblicalText.path.label("path_biblical"),
                BiblicalText.filename.label("filename_biblical"),
                HistoricalText.text[ConvertIndexHistorical.lineIndex - 1 : ConvertIndexHistorical.lineIndex + 4].label("historical_text"),
                BiblicalText.text[ConvertIndexBiblical.lineIndex - 1 : ConvertIndexBiblical.lineIndex + 4].label("biblical_text"),
            )
            .join(BiblicalText, BiblicalText.id == TextHighlights.biblical_text_id)
            .join(TextUser, TextUser.id == TextHighlights.text_user_id)
            .join(HistoricalText, HistoricalText.id == TextUser.text_id)
            .join(ConvertIndexHistorical, ConvertIndexHistorical.id == TextHighlights.historical_start_line)
            .join(ConvertIndexBiblical, ConvertIndexBiblical.id == TextHighlights.biblical_start_line)
            .where(
                HistoricalText.filename == filename,
                HistoricalText.path == path,
                TextUser.user_id == user.id
            )
            .order_by(BiblicalText.path, BiblicalText.filename)
        )

        for row in qRes:
            key = (row.path_biblical, row.filename_biblical)
            if key not in groups:
                groups[key] = []

            groups[key].append({
                "color_id": row.color_id,
                "historical_start_line": row.historical_start_line,
                "biblical_start_line": row.biblical_start_line,
                "historical_range_word": {"startWord": row.historical_range_word.lower, "endWord": row.historical_range_word.upper-1},
                "biblical_range_word": {"startWord": row.biblical_range_word.lower, "endWord": row.biblical_range_word.upper-1},
                "historical_text": row.historical_text[0:5],
                "biblical_text":  row.biblical_text[0:5],
                "historical_more_line": len(row.historical_text)==6,
                "biblical_more_line": len(row.biblical_text)==6
            })

        return [
            {
                "path": bib_path,
                "filename": bib_filename,
                "highlights": highlights,
            } for (bib_path, bib_filename), highlights in groups.items()
        ]

def insert_new_highlights(
    urn_b,
    start_b,end_b,
    line_start_b,
    h_id_text,
    start_h,end_h,user
):
    with session_scope() as s:

        user_assoc = s.execute(
            select(TextUser)
            .where(
                TextUser.user_id == user.id,
                TextUser.text_id == h_id_text
            )
        ).scalar()
        if not user_assoc:
            raise PermissionError("Utente non autorizzato ad aggiungere evidenziazioni a questo testo.")

        path_b, filename_b = parse_urn(urn_b)

        biblical_text_id = s.execute(
            select(BiblicalText.id)
            .where(
                BiblicalText.filename == filename_b,
                BiblicalText.path == path_b,
            )
        ).scalar_one()

        already_highlighted = s.execute(
            select(TextHighlights.id)
            .join(TextUser, TextUser.id == TextHighlights.text_user_id)
            .where(
                TextHighlights.biblical_text_id == biblical_text_id,
                TextUser.text_id == h_id_text,
                TextHighlights.historical_range_word.op("&&")(func.int4range(start_h, end_h+1)),
                TextHighlights.biblical_range_word.op("&&")(func.int4range(start_b, end_b+1)),
            )
        ).first()

        if already_highlighted is not None:
            raise ValueError("highlight already exists in this range")
        
        historical_start_line = s.execute(
            select(ConvertIndexHistorical.id)
            .where(
                ConvertIndexHistorical.textId == h_id_text,
                ConvertIndexHistorical.wordIndexRange.op("@>")(start_h)
            )
        ).scalar_one()

        biblical_start_line = s.execute(
            select(ConvertIndexBiblical.id)
            .where(
                ConvertIndexBiblical.textId == biblical_text_id,
                ConvertIndexBiblical.lineIndex == line_start_b,
            )
        ).scalar_one()

        new_highlight = TextHighlights(
            color_id=1,
            biblical_text_id=biblical_text_id,
            text_user_id=user_assoc.id,
            biblical_range_word=NumericRange(start_b, end_b+1),
            historical_range_word=NumericRange(start_h, end_h+1),
            historical_start_line=historical_start_line,
            biblical_start_line=biblical_start_line,
        )
        s.add(new_highlight)
        s.commit()
        s.refresh(new_highlight)
