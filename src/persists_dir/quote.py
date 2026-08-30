from psycopg2.extras import NumericRange
from sqlalchemy import func, select, exists, and_, or_

from settings import LINE_EXTRACT_UPPER,LINE_EXTRACT_LOWER
from db import session_scope
from model import *
from schemas import *
from util import parse_urn

def check_texts_exist(s, idH: int, idB: int):
    h_exists = bool(s.scalar(select(exists().where(HistoricalText.id == idH))))
    b_exists = bool(s.scalar(select(exists().where(BiblicalText.id == idB))))
    if not h_exists or not b_exists:
        raise ValueError("Testo non trovato")

def common_get_quotes(rows) -> dict:
    grouped = dict()
    if rows:
        for r in rows:
            grouped[r.id] = {
                "color": r.color_id,
                "biblical": {"startWord": r.biblical_range_word.lower, "endWord": r.biblical_range_word.upper - 1},
                "historical": {"startWord": r.historical_range_word.lower, "endWord": r.historical_range_word.upper - 1},
            }
    
    return grouped


def get_quotes(idH: int, idB: int) -> dict:
    with session_scope() as s:
        stmt = ( 
            select(TextHighlights)
            .where(
                TextHighlights.biblical_text_id == idB,
                TextHighlights.historical_text_id == idH,
            )
        )
        rows = s.scalars(stmt).all()
        grouped = common_get_quotes(rows)
        if not grouped:
            check_texts_exist(s, idH, idB)
        return grouped

def get_quotes_portion(idH: int, idB: int, lineB: int, lineH: int) -> dict:
    with session_scope() as s:
        stmt = (
            select(TextHighlights)
            .where(
                TextHighlights.biblical_text_id == idB,
                TextHighlights.historical_text_id == idH
            )
            .join(ConvertIndexBiblical, ConvertIndexBiblical.id == TextHighlights.biblical_start_line)
            .join(ConvertIndexHistorical, ConvertIndexHistorical.id == TextHighlights.historical_start_line)
            .where(
                or_(
                    and_(
                        ConvertIndexBiblical.lineIndex >= lineB - LINE_EXTRACT_LOWER,
                        ConvertIndexBiblical.lineIndex <= lineB + LINE_EXTRACT_UPPER
                    ),
                    and_(
                        ConvertIndexHistorical.lineIndex >= lineH - LINE_EXTRACT_LOWER,
                        ConvertIndexHistorical.lineIndex <= lineH + LINE_EXTRACT_UPPER
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
    toUpdate: HighlightUpdate
):
    with session_scope() as s:
        stmt = select(TextHighlights).where(TextHighlights.id == id)
        result = s.scalar(stmt)

        if result is None:
            raise ValueError("Highlight non trovato")
        
        if toUpdate.color is not None:
            result.color_id = toUpdate.color
        if toUpdate.historical is not None:
            historical_start_line = s.execute(
                select(ConvertIndexHistorical.id)
                .where(
                    ConvertIndexHistorical.textId == result.historical_text_id,
                    ConvertIndexHistorical.lineIndex == toUpdate.historical.startLine,
                )
            ).scalar_one()
            result.historical_range_word = NumericRange(toUpdate.historical.startWord, toUpdate.historical.endWord + 1)
            result.historical_start_line = historical_start_line
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

        s.commit()
        s.refresh(result)

def delete_highlight(id: int):
    with session_scope() as s:
        stmt = select(TextHighlights).where(TextHighlights.id == id)
        deleteMe = s.scalar(stmt)
        if deleteMe is None:
            raise ValueError("Highlight non trovato") 
        
        s.delete(deleteMe)
        s.commit()

def list_all_historical_highlights(
    path: str,
    filename: str,
):
    with session_scope() as s:
        groups: dict[tuple[str, str], list] = {}

        qRes = s.execute(
                select(
                    ConvertIndexBiblical.lineIndex.label("biblical_start_line"),
                    ConvertIndexHistorical.lineIndex.label("historical_start_line"),
                    TextHighlights.color_id,
                    TextHighlights.biblical_range_word,
                    TextHighlights.historical_range_word,
                    HistoricalText.path.label("path_historical"),
                    HistoricalText.filename.label("filename_historical"),
                    BiblicalText.text[ConvertIndexBiblical.lineIndex - 1 : ConvertIndexBiblical.lineIndex + 3].label("biblical_text"),
                    HistoricalText.text[ConvertIndexHistorical.lineIndex - 1 : ConvertIndexHistorical.lineIndex + 3].label("historical_text"),
                )
                .join(HistoricalText, HistoricalText.id == TextHighlights.historical_text_id)
                .join(BiblicalText, BiblicalText.id == TextHighlights.biblical_text_id)
                .join(ConvertIndexBiblical, ConvertIndexBiblical.id == TextHighlights.biblical_start_line)
                .join(ConvertIndexHistorical, ConvertIndexHistorical.id == TextHighlights.historical_start_line)
                .where(
                    BiblicalText.filename == filename,
                    BiblicalText.path == path,
                )
                .order_by(HistoricalText.path, HistoricalText.filename)
            )

        for row in qRes:
            key = (row.path_historical, row.filename_historical)
            if key not in groups:
                groups[key] = []
            groups[key].append({
                "color_id": row.color_id,
                "biblical_start_line":   row.biblical_start_line,
                "historical_start_line": row.historical_start_line,
                "biblical_range_word":   {"startWord": row.biblical_range_word.lower, "endWord": row.biblical_range_word.upper-1},
                "historical_range_word": {"startWord": row.historical_range_word.lower, "endWord": row.historical_range_word.upper-1},
                "biblical_text":         row.biblical_text,
                "historical_text":       row.historical_text,
            })

        return [
            {
                "path": bib_path,
                "filename": bib_filename,
                "highlights": highlights,
            } for (bib_path, bib_filename), highlights in groups.items()
        ]

def insert_new_highlights(urn_h,start_h,end_h,line_start_h,b_id_text,start_b,end_b):
    with session_scope() as s:

        path_h, filename_h = parse_urn(urn_h)

        historical_text_id = s.execute(
            select(HistoricalText.id)
            .where(
                HistoricalText.filename == filename_h,
                HistoricalText.path == path_h,
            )
        ).scalar_one()

        already_highlighted = s.execute(
            select(TextHighlights.id)
            .where(
                TextHighlights.historical_text_id == historical_text_id,
                TextHighlights.biblical_text_id == b_id_text,
                TextHighlights.biblical_range_word.op("&&")(func.int4range(start_b, end_b+1)),
                TextHighlights.historical_range_word.op("&&")(func.int4range(start_h, end_h+1)),
            )
        ).first()

        if already_highlighted is not None:
            raise ValueError("highlight already exists in this range")
        
        line_start_b = s.execute(
            select(ConvertIndexBiblical.id)
            .where(
                ConvertIndexBiblical.textId == b_id_text,
                ConvertIndexBiblical.wordIndexRange.op("&&")(func.int4range(start_b, end_b+1))
            )
        ).scalar_one()

        historical_start_line = s.execute(
            select(ConvertIndexHistorical.id)
            .where(
                ConvertIndexHistorical.textId == historical_text_id,
                ConvertIndexHistorical.lineIndex == line_start_h,
            )
        ).scalar_one()

        new_highlight = TextHighlights(
            color_id=1,
            historical_text_id=historical_text_id,
            biblical_text_id=b_id_text,
            historical_range_word=NumericRange(start_h, end_h+1),
            biblical_range_word=NumericRange(start_b, end_b+1),
            biblical_start_line=line_start_b,
            historical_start_line=historical_start_line,
        )
        s.add(new_highlight)
        s.commit()
        s.refresh(new_highlight)
