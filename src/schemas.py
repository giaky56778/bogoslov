from pydantic import BaseModel, model_validator
from typing import Optional

class RangeSchema(BaseModel):
    startLine: int
    startWord: int
    endWord:   int

class HighlightUpdate(BaseModel):
    color:       int | None = None
    historical:  RangeSchema | None = None
    biblical:    RangeSchema | None = None

class HybridResult(BaseModel):
    urn: str
    score: float
    text: str
    algos: list[str]

class OptionalSearch(BaseModel):
    original_path:str
    original_filename:str
    offset:int

class QuoteCreate(BaseModel):
    urn_h: str
    start_h: int
    end_h: int
    line_start_h: int
    b_id_text: int
    start_b: int
    end_b: int

class TextQuery(BaseModel):
    text_id: int | None = None
    path: str | None = None
    filename: str | None = None

    @model_validator(mode="after")
    def check_text_identifier(self):
        if not (((self.path is not None) and (self.filename is not None)) or self.text_id is not None):
            raise ValueError("Specificare 'path' e 'filename' oppure 'text_id'")
        return self

class TextPortionQuery(BaseModel):
    text_id: int | None = None
    path: str | None = None
    filename: str | None = None
    line: int | None = None
    lineNumber: str | None = None
    wordId: int | None = None

    @model_validator(mode="after")
    def check_portion_parameters(self):
        if not (((self.path is not None) and (self.filename is not None)) or self.text_id is not None):
            raise ValueError("Specificare 'path' e 'filename' oppure 'text_id'")
        
        parameterNotNone = [v for v in (self.line, self.lineNumber, self.wordId) if v is not None]
        if len(parameterNotNone) != 1:
            raise ValueError("Specificare esattamente uno tra 'line', 'lineNumber' e 'wordId'")
        return self

class QuotesQuery(BaseModel):
    historical_text_id: int
    biblical_text_id: int

class QuotesQueryPartition(BaseModel):
    historical_text_id: int
    biblical_text_id: int
    lineB: int
    lineH: int

class HybridSearchQuery(BaseModel):
    fulltext: str
    algoList: list[str]
    sources: str
    k: int | None = 60

class XlsxResultsQuery(BaseModel):
    filename: str
    path_b: str | None = None
    filename_b: str | None = None
    search_start: int | None = None
    search_end: int | None = None

    @model_validator(mode="after")
    def check_all_or_none(self):
        params = (self.path_b, self.filename_b, self.search_start, self.search_end)
        not_none_count = sum(v is not None for v in params)
        if not_none_count not in (0, 4):
            raise ValueError("Every params need to be all None, or all not None")
        return self

class SearchJsonQuery(BaseModel):
    filename: str
    original_path: str | None = None
    original_filename: str | None = None
    search_start: int | None = None
    search_end: int | None = None
    offset: int | None = None

    @model_validator(mode="after")
    def check_all_or_none(self):
        params = (self.original_path, self.original_filename, self.search_start, self.search_end,self.offset)
        not_none_count = sum(v is not None for v in params)
        if not_none_count not in (0, 5):
            raise ValueError("Every params need to be all None, or all not None")
        return self
    
class HighlightHistoricalQuery(BaseModel):
    filename: str
    path: str

class TextIdQuery(BaseModel):
    filename: str
    path: str

class GetLineFromIndexBQuery(BaseModel):
    original_path: str
    original_filename: str
    search_start: int
