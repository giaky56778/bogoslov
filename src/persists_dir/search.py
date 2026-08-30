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
        #print(run)
        return run

    def offsetWordFinder(toFind:str, path, filename, start, end, s):
        stmt = (
            select(HistoricalText.text[start+1:end+1])
            .where(HistoricalText.path == path, HistoricalText.filename == filename)
        )
        qT = s.execute(stmt).scalar_one()


        fixFind=''
        for word in toFind.lower().split():
            strip=strip_punctuation(word)
            if strip:
                fixFind+=strip+' '
        fixFind=fixFind.strip()

        t = ''
        splitText = []
        char_to_token = {}
        current_char = 0
        token_index = 0
        
        for segment in qT:
            for token in segment["text"]:
                word = strip_punctuation(token["word"])
                splitText.append(word)
                if word:
                    char_to_token[current_char] = token_index
                    t += word + ' '
                    current_char += len(word) + 1
                token_index += 1
        t = t.strip()
        
        charResult = t.lower().find(fixFind)
        if charResult == -1:
            return -1

        matched_token_index = 0
        end_token_index = 0
        end_charResult = charResult + len(fixFind) - 1

        for char_idx in sorted(char_to_token.keys()):
            if char_idx <= charResult:
                matched_token_index = char_to_token[char_idx]
            if char_idx <= end_charResult:
                end_token_index = char_to_token[char_idx]
                
        return matched_token_index, end_token_index
    
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

        offset_result = offsetWordFinder(cleaned_found, path, filename, start_line, end_line, s)
        if offset_result == -1:
            return None

        start_offset, end_offset = offset_result
        print('offset', start_offset, end_offset)

        return {
            "startWordId": int(start_word_id) + start_offset,
            "endWordId": int(start_word_id) + end_offset,
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

            print("qR",qR)

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

            print('highlight:',highlight)

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

            print('\npath_b=',path_b,'\nfilename_b=',filename_b,'\npath_h=',path,'\nfilename_h=',filename,'\nlowerBound=',highlight["startWordId"],'\nupperBound=',highlight["endWordId"])

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
  