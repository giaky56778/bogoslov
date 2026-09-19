from pydantic import BaseModel, model_validator
from fastapi import UploadFile, File, Form

class RangeSchema(BaseModel):
    startLine: int
    startWord: int
    endWord:   int

class HighlightUpdate(BaseModel):
    color:     int | None = None
    biblical:  RangeSchema | None = None
    historical:RangeSchema | None = None

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
    urn_b: str
    start_b: int
    end_b: int
    line_start_b: int
    h_id_text: int
    start_h: int
    end_h: int

class TextQuery(BaseModel):
    text_id: int | None = None
    path: str | None = None
    filename: str | None = None

    @model_validator(mode="after")
    def check_text_identifier(self):
        if not (((self.path is not None) and (self.filename is not None)) or self.text_id is not None):
            raise ValueError("Erorr: provide only path and filename or only text_id")
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
            raise ValueError("Erorr: provide only path and filename or only text_id")
        
        parameterNotNone = [v for v in (self.line, self.lineNumber, self.wordId) if v is not None]
        if len(parameterNotNone) != 1:
            raise ValueError("Erorr: provide exactly only one of line, lineNumber or wordId")
        return self

class QuotesQuery(BaseModel):
    biblical_text_id: int
    historical_text_id: int

class QuotesQueryPartition(BaseModel):
    biblical_text_id: int
    historical_text_id: int
    lineB: int
    lineH: int

class HybridSearchQuery(BaseModel):
    fulltext: str
    algoList: list[str]
    sources: str
    k: int | None = 60

    @model_validator(mode="after")
    def check_all_or_none(self):
        if self.k is not None and self.k <= 0 :
            raise ValueError("Error: k cannot be negative or 0")
        return self

class XlsxResultsQuery(BaseModel):
    filename: str
    path_h: str | None = None
    filename_h: str | None = None
    search_start: int | None = None
    search_end: int | None = None

    @model_validator(mode="after")
    def check_all_or_none(self):
        params = (self.path_h, self.filename_h, self.search_start, self.search_end)
        not_none_count = sum(v is not None for v in params)
        if not_none_count not in (0, 4):
            raise ValueError("Error: every params need to be all None, or all not None")
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
            raise ValueError("Error: every params need to be all None, or all not None")
        return self

class UploadTextQuery:
    # cannot be BaseModel, Form and File break the server endpoint
    def __init__(
        self,
        path: str = Form(...),
        filename: str = Form(...),
        file: UploadFile | None = File(None),
        text: str | None = Form(None)
    ):
        self.path = path
        self.filename = filename
        self.file = file
        self.text = text
        
        notNone = [v for v in (self.file, self.text) if v is not None]
        if len(notNone) != 1:
            raise ValueError("Error: you must provide exactly one of 'file' or 'text'")

class HighlightBiblicalQuery(BaseModel):
    filename: str
    path: str

class TextIdQuery(BaseModel):
    filename: str
    path: str

class GetLineFromIndexBQuery(BaseModel):
    original_path: str
    original_filename: str
    search_start: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
