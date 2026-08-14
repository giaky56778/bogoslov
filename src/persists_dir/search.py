from sqlalchemy import func, select, and_, or_, exists

from db import session_scope
from model import *
from schemas import *
from util import strip_punctuation

def obtain_range_word(startSearch:int,endSearch:int, path_b: str, filename_b: str, texts):
        
    def find_already_highlighted(
        path_h: str,
        filename_h: str,
        path_b: str,
        filename_b: str,
        historical_lower_bound: int,
        historical_upper_bound: int,
        biblical_lower_bound: int,
        biblical_upper_bound: int,
        s
    ):
        occupied = exists(
            select(1)
            .select_from(TextHighlights)
            .join(HistoricalText, TextHighlights.historical_text_id == HistoricalText.id)
            .join(BiblicalText, TextHighlights.biblical_text_id == BiblicalText.id)
            .where(
                and_(
                    HistoricalText.path == path_h,
                    HistoricalText.filename == filename_h,
                    BiblicalText.filename == filename_b,
                    BiblicalText.path == path_b,
                    or_(
                        func.coalesce(
                            TextHighlights.historical_range_word.op("&&")(
                                func.int4range(historical_lower_bound, historical_upper_bound+1)
                            ),
                            False,
                        ),
                        func.coalesce(
                            TextHighlights.biblical_range_word.op("&&")(
                                func.int4range(biblical_lower_bound, biblical_upper_bound+1)
                            ),
                            False,
                        ),
                    ),
                )
            )
        )
        stmt = select(occupied.label("occupied"))
        run=s.execute(stmt).scalar()
        return run

    def offsetWordFinder(toFind:str, path, filename, start, end, s):
        stmt = (
            select(HistoricalText.text[start+1:end+1])
            .where(HistoricalText.path == path, HistoricalText.filename == filename)
        )
        qT = s.execute(stmt).scalar_one()


        fixFind=''
        for word in toFind.lower().split():
            fixFind+=strip_punctuation(word)+' '
        fixFind=fixFind.strip()

        t = ''
        splitText=[]
        for segment in qT:
            for token in segment["text"]:
                word = strip_punctuation(token["word"])
                splitText.append(word)
                if word:
                    t += word+' '
        t=t.strip()
        charResult = t.lower().find(fixFind)
        #  0 = from char 0
        # -1 = don't exist
        if charResult==-1 or charResult==0:
            return charResult
        
        wordPosOffset = 1

        for i in range(len(splitText)):
            value=splitText[i]
            strip=value.strip()
            if not len(strip)==0:
                charResult -= len(value)+1
            
            if charResult <=0 and len(splitText[i].strip())!=0:
                if charResult<0:
                    return wordPosOffset-1
                return wordPosOffset
            
            wordPosOffset += 1
            
        return wordPosOffset+1
    
    def can_highlight_words(
        found: str,
        path: str,
        filename: str,
        start_line: int,
        end_line: int,
        start_word_id: int,
        s,
    ):
        cleaned_found = found.strip()
        if not cleaned_found:
            return None

        offset = offsetWordFinder(cleaned_found, path, filename, start_line, end_line, s)
        if offset == -1:
            return None

        words = cleaned_found.split()
        return {
            "startWordId": int(start_word_id) + offset,
            "endWordId": int(start_word_id) + offset + len(words) -1,
        }

    with session_scope() as s:
        result = []
        for value in texts:
            left, right = value["urn"].split(":")
            parts = left.split(".")

            path = ".".join(parts[:-1])
            filename = parts[-1]
            index = right.replace(".", "_")

            line_index = "\\_".join(index.split("_")) + "\\_%"

            qR = s.execute(
                select(
                    func.min(func.lower(ConvertIndexHistorical.wordIndexRange)).label("startWordId"),
                    func.max(func.upper(ConvertIndexHistorical.wordIndexRange)).label("endWordId"),
                    func.min(ConvertIndexHistorical.lineIndex).label("startLine"),
                    func.max(ConvertIndexHistorical.lineIndex).label("endLine"),
                )
                .join(HistoricalText, HistoricalText.id == ConvertIndexHistorical.textId)
                .where(
                    HistoricalText.path == path,
                    HistoricalText.filename == filename,
                    ConvertIndexHistorical.lineRange.like(line_index, escape="\\"),
                )
            ).first()

            if not qR or qR.startWordId is None:
                result.append({
                    "text": value,
                    "range": {
                        "startWordId": None,
                        "endWordId": None,
                        "startLine": None,
                        "endLine": None,
                        "error": -1,
                    }
                })
                continue

            highlight = can_highlight_words(
                found=value["found"],
                path=path,
                filename=filename,
                start_line=qR.startLine,
                end_line=qR.endLine,
                start_word_id=qR.startWordId,
                s=s,
            )

            if highlight is None:
                result.append({
                    "text": value,
                    "range": {
                        "startWordId": int(qR.startWordId),
                        "endWordId": int(qR.endWordId)-1,
                        "startLine": qR.startLine,
                        "endLine": qR.endLine,
                        "error": 0,
                    }
                })
                continue
            
            if find_already_highlighted(
                path_h=path,
                filename_h=filename,
                path_b=path_b,
                filename_b=filename_b,
                historical_lower_bound=highlight["startWordId"],
                historical_upper_bound=highlight["endWordId"],
                biblical_lower_bound=startSearch,
                biblical_upper_bound=endSearch,
                s=s,
            ):
                result.append({
                    "text": value,
                    "range": {
                        "startWordId": None,
                        "endWordId": None,
                        "startLine": None,
                        "endLine": None,
                        "error": 1,
                    }
                })
                continue

            result.append({
                "text": value,
                "range": {
                    "startWordId": highlight["startWordId"],
                    "endWordId": highlight["endWordId"],
                    "startLine": qR.startLine,
                    "endLine": qR.endLine,
                    "error": 0,
                }
            })
        return result
  