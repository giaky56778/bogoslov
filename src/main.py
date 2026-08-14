#!/usr/bin/env python3
"""The BogoSlov API, see 4euplus.eu/4EU-1150.html and https://ceur-ws.org/Vol-3937/short8.pdf"""

from typing import Annotated, Callable
from enum import Enum
from pathlib import Path
import asyncio
import json
import xml.etree.ElementTree as ET

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Response, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import gradio as gr

from settings import ms2source, examples, port, lang, ALGO_NOT_FULL_LINE,LIMIT_RESULT,STRANS_TOOLPIT,ALGO_TOOLPIT,ALLOWED_ORIGINS,API_ADDRESS
from persist import *
from persists_dir import *
from results import render_excel, render_excel_hybrid, render_html, render_json, render_json_hybrid
from util import merge_hybrid_raw
from tei_converter import convert_tei_upload, plain_text_to_rows
from cache import store_search_result, get_search_result, purge_expired_search_results
from schemas import *

import app_regex
import app_lcs
import app_ngram
import app_strans
import app_bm25

import logging

logging.basicConfig(level=logging.DEBUG)

all_sources = "".join(ms2source.keys())
strans_models = {m.split("/")[1]: m for m in get_strans_models()}
mime_xlsx = "application/vnd.ms-excel"
headers_xlsx = {"content-type": mime_xlsx}

algos: dict[str, Callable[[list[str], str], list[tuple[str, str, float]]]] = {
    "regex": app_regex.find,
    "lcs": app_lcs.find,
    "ngram": app_ngram.find,
    "bm25": app_bm25.find,
}


class SearchParams(BaseModel):
    sources: str = Field(
        default=all_sources,
        description="Concatenated initials of sources to search in, see /settings for initial interpretations.",
        examples=[all_sources],
    )
    fulltext: str = Field(
        description="The text to query for quotations.", examples=examples
    )
    result_format: str = Field(
        default="html",
        description="File format of the output.",
        examples=["html", "json", "xlsx"],
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(purge_expired_search_results())
    yield

app = FastAPI(
    title=f"BogoSlov ({lang})",
    description=__doc__,
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "text", "description": "API for interact with biblical and historical text"},
        {"name": "quote", "description": "API for interact with confirmed quotes of the text."},
        {"name": "search", "description": "API for search around primary text."},
        {"name": "info", "description": "API for metadata and auxiliary data."}
    ],
)

def singleAlgoCall(algo: str, fulltext: str, src: str):
    """Call a single algorithm with a list of source initials and the query text."""

    sources:list[ms2source] = [ms2source[s] for s in src]

    if algo in algos:
        result = algos[algo](sources, fulltext)
    elif algo in strans_models.keys():
        result = app_strans.find(sources, fulltext, model=strans_models[algo])
    else:
        raise ValueError("Algorithm not found")

    return result

@app.get("/api/{algo}", tags=["search"])
async def query(algo: str, search: Annotated[SearchParams, Query()]):
    params = {
        "query": search.fulltext,
        "method": algo,
        "sources": search.sources,
    }

    result = singleAlgoCall(algo, search.fulltext, search.sources)

    if not result:
        raise HTTPException(204, detail="No results")

    if search.result_format == "html":
        return HTMLResponse(content=render_html(result))
    if search.result_format == "json":
        return JSONResponse(content=render_json(result))
    if search.result_format == "xlsx":
        fname = render_excel(params, result)
        fpath = f"/results/{fname}"
        if Path(fpath).exists():
            return FileResponse(
                fpath,
                status_code=201,
                filename=fname,
                media_type=mime_xlsx,
                headers=headers_xlsx,
            )
        else:
            raise HTTPException(500, detail="File not exported.")


gr.mount_gradio_app(app, app_regex.interface(), path="/regex")
gr.mount_gradio_app(app, app_lcs.interface(), path="/lcs")
gr.mount_gradio_app(app, app_ngram.interface(), path="/ngram")
gr.mount_gradio_app(app, app_strans.interface(), path="/strans")
gr.mount_gradio_app(app, app_bm25.interface(), path="/bm25")


@app.get("/settings", tags=["info"])
async def settings():
    """Returns the language of the installation. Also serves as healthcheck"""
    return JSONResponse(
        content={
            "version": app.version,
            "language": lang,
            "sources": ms2source,
            "sentence_transformer_models": {
                m.split("/")[1]: m for m in strans_models.values()
            },
            "explicit_algorithms": list(algos.keys()),
        },
        status_code=200,
    )

###########
# For frontend
###########

# CORS Configuration (for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(f"{API_ADDRESS}/text/getHistoricalText/", tags=["text"])
async def getHistoricalText(query: Annotated[TextQuery, Query()]):
            
    try:
        text, chapter, index, textId = get_full_text_by_tables(HistoricalText, ConvertIndexHistorical, query)
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

    return JSONResponse(
        content={
            "text": text,
            "chapter": chapter,
            "index": index,
            "textId": textId
        },
        status_code=200,
    )

@app.get(f"{API_ADDRESS}/text/getHistoricalTextPortion/", tags=["text"])
async def getHistoricalTextPortion(query: Annotated[TextPortionQuery, Query()]):
            
    try:
        text, chapter, index, textId = get_portion_text_by_tables(HistoricalText, ConvertIndexHistorical, query)
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

    return JSONResponse(
        content={
            "text": text,
            "chapter": chapter,
            "index": index,
            "textId": textId
        },
        status_code=200,
    )

@app.get(f"{API_ADDRESS}/text/getHistoricalTextNames", tags=["text"])
async def getHistoricalTextNames():
    result = get_text_name_by_table(HistoricalText)

    return JSONResponse(
        content=result,
        status_code=200
    )

@app.get(f"{API_ADDRESS}/text/getBiblicalText/", tags=["text"])
async def getBiblicalText(query: Annotated[TextQuery, Query()]):
    try:
        text, chapter, index, textId = get_full_text_by_tables(BiblicalText, ConvertIndexBiblical, query)
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

    return JSONResponse(
        content={
            "text": text,
            "chapter": chapter,
            "index": index,
            "textId": textId
        },
        status_code=200
    )

@app.get(f"{API_ADDRESS}/text/getBiblicalTextPortion/", tags=["text"])
async def getBiblicalTextPortion(query: Annotated[TextPortionQuery, Query()]):
    try:
        text, chapter, index, textId = get_portion_text_by_tables(BiblicalText, ConvertIndexBiblical, query)
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

    return JSONResponse(
        content={
            "text": text,
            "chapter": chapter,
            "index": index,
            "textId": textId
        },
        status_code=200
    )

@app.get(f"{API_ADDRESS}/text/getBiblicalTextNames", tags=["text"])
async def getBiblicalTextNames():
    result = get_text_name_by_table(BiblicalText)

    return JSONResponse(
        content=result,
        status_code=200
    )

@app.get(f"{API_ADDRESS}/quote/getQuotes", tags=["quote"])
async def getQuotes(query: Annotated[QuotesQuery, Query()]):
    result=get_quotes(query.historical_text_id,query.biblical_text_id)
    if len(result)==0:
        return Response(status_code=204)

    return JSONResponse(
        content=result,
        status_code=200
    )

@app.get(f"{API_ADDRESS}/quote/getQuotesPortion", tags=["quote"])
async def getQuotesPortion(query: Annotated[QuotesQueryPartition, Query()]):
    result=get_quotes_portion(query.historical_text_id,query.biblical_text_id,query.lineB,query.lineH)
    if len(result)==0:
        return Response(status_code=204)

    return JSONResponse(
        content=result,
        status_code=200
    )

@app.patch(f"{API_ADDRESS}/quote/updateQuote/{{id}}", tags=["quote"])
async def updateQuote(
    id: int,
    body: HighlightUpdate,
):
    try:
        update_quotes(id,body)
        return Response(status_code=204)
    except ValueError:
        raise HTTPException(status_code=404, detail="Highlight non trovato")

@app.delete(f"{API_ADDRESS}/quote/deleteQuote/{{id}}", tags=["quote"])
async def deleteQuote(id: int):
    try:
        delete_highlight(id)
        return Response(status_code=204)
    except ValueError:
        raise HTTPException(status_code=404, detail="Highlight non trovato")
    
@app.get(f"{API_ADDRESS}/search/hybridSearch", tags=["search"])
async def hybridSearch(query: Annotated[HybridSearchQuery, Query()]):
    async def event_stream():

        def sse_event(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        texts = dict()
        scores = dict()
        deferred_algos = []

        yield sse_event("search-start",{"start":True})
        for algo in query.algoList:
            if algo in ALGO_NOT_FULL_LINE:
                deferred_algos.append(algo)
                continue

            raw = await asyncio.to_thread(singleAlgoCall, algo, query.fulltext, query.sources)
            merge_hybrid_raw(query.k, algo, raw, texts, scores)
            yield sse_event("search-complete", {"algo": algo})

        for algo in deferred_algos:
            raw = await asyncio.to_thread(singleAlgoCall, algo, query.fulltext, query.sources)
            merge_hybrid_raw(query.k, algo, raw, texts, scores, problematic=True)
            yield sse_event("search-complete", {"algo": algo})

        scoresSorted = dict(sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True))
        result = render_json_hybrid(texts=texts, scores=scoresSorted)
        params = {
            "query": query.fulltext,
            #"method": "hybrid",
            "sources": query.sources,
        }
        name = await store_search_result(params, result)
        yield sse_event("complete", {
            "filename": name,
            "total_results": len(result),
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get(f"{API_ADDRESS}/search/getSearchXlsx/", tags=["search"])
async def getSearchXlsx(query: Annotated[XlsxResultsQuery, Query()]):
    try:
        cached = await get_search_result(query.filename)
    except ValueError:
        raise HTTPException(status_code=404, detail="file not found")

    urn_b = f"{query.path_b}.{query.filename_b}" if query.path_b and query.filename_b else None

    
    xlsx_bytes = render_excel_hybrid(
        cached.params,
        cached.result,
        urn_b=urn_b,
        h_start=query.search_start,
        h_end=query.search_end,
    )

    return Response(
        content=xlsx_bytes,
        status_code=201,
        media_type=mime_xlsx,
        headers={
            **headers_xlsx,
            "Content-Disposition": f'attachment; filename="{query.filename}"',
        },
    )

@app.get(f"{API_ADDRESS}/search/getSearchJson/", tags=["search"])
async def getSearchJson(query: Annotated[SearchJsonQuery, Query()]):
    try:
        cached = await get_search_result(query.filename)
    except ValueError:
        raise HTTPException(status_code=404, detail="file not found")

    data = cached.result

    # If is from a texts
    if query.original_path and query.original_filename and query.offset is not None and query.search_start is not None and query.search_end is not None:
        max_offset = len(data) // LIMIT_RESULT
        if query.offset < 0 or query.offset > max_offset:
            raise HTTPException(status_code=422, detail="offset out of bounds")

        start = query.offset * LIMIT_RESULT
        resultSearchOffset = data[start:start + LIMIT_RESULT]
        resultRange=obtain_range_word(
            path_b=query.original_path,
            filename_b=query.original_filename,
            texts=resultSearchOffset,
            startSearch=query.search_start,
            endSearch=query.search_end
        )

        lineIndex=get_biblical_line_index_by_word(
            path=query.original_path,
            filename=query.original_filename,
            word_id=query.search_start,
        )

        return JSONResponse(
            content={
                "results": resultRange,
                "lineIndex": lineIndex,
            },
            status_code=200,
        )

    # If is from a write sentence
    query_text = str(cached.params.get("query", ""))
    result = [{"text": item, "query": query_text} for item in data]
    return JSONResponse(content = {"results":result}, status_code=200)

@app.get(f"{API_ADDRESS}/info/getAlgoToolpit/", tags=["info"])
async def getToolTip():
    result={
        "algo":ALGO_TOOLPIT,
        "strans":STRANS_TOOLPIT
    }
    return JSONResponse(content= result, status_code=200)

@app.get(f"{API_ADDRESS}/info/getAllHighlightHistorical", tags=["quote"])
async def getAllHighlightHistorical(query: Annotated[HighlightHistoricalQuery, Query()]):
    return JSONResponse(
        content=list_all_historical_highlights(path=query.path, filename=query.filename),
        status_code=200,
    )


@app.post(f"{API_ADDRESS}/quote/saveQuote", tags=["quote"])
async def saveQuote(body: QuoteCreate):
    try:
        insert_new_highlights(
            body.urn_h,
            body.start_h,
            body.end_h,
            body.line_start_h,
            body.b_id_text,
            body.start_b,
            body.end_b
        )
    except ValueError:
        raise HTTPException(status_code=409, detail="highlight already exists in this range")

    return Response(status_code=201)

@app.post(f"{API_ADDRESS}/text/upload", tags=["text"])
async def uploadBiblicalText(
    path: str = Form(...),
    filename: str = Form(...),
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):

    def validate_path_component(value: str):
        if not value or "/" in value or "\\" in value or value in (".", ".."):
            raise HTTPException(status_code=422, detail=f"Invalid name")

    validate_path_component(path)
    validate_path_component(filename)

    if biblical_text_exists(path, filename):
        raise HTTPException(status_code=409, detail="Biblical text already exists for this path/filename")

    if file is not None and (file.filename or "").lower().endswith((".xml")):
        try:
            rows = convert_tei_upload(file)
        except ET.ParseError:
            raise HTTPException(status_code=422, detail="Invalid TEI/XML file")
    else:
        if file is not None:
            raw_text = (await file.read()).decode("utf-8", errors="replace")
        elif text is not None:
            raw_text = text
        else:
            raise HTTPException(status_code=422, detail="Provide either a TEI file or plain text")

        rows = plain_text_to_rows(filename,raw_text)

    if not rows:
        raise HTTPException(status_code=422, detail="No text content found")

    biblical_id = persist_biblical_text(path, filename, rows)
    return JSONResponse(
        content={
            "id": biblical_id
        }, 
        status_code=201
    )
    
@app.delete(f"{API_ADDRESS}/text/deleteBiblicalText", tags=["text"])
async def deleteBiblicalText(id: int):
    try:
        delete_text(id)
        return Response(status_code=204)
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

@app.get(f"{API_ADDRESS}/text/biblicalWordIdToLine", tags=["info"])
async def biblicalWordIdToLine(query: Annotated[GetLineFromIndexBQuery, Query()]):
    try:
        return JSONResponse(
            content={
                 "lineIndex": get_biblical_line_index_by_word(
                                path=query.original_path,
                                filename=query.original_filename,
                                word_id=query.search_start,
                            )
            }, 
            status_code=201
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Testo non trovato")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)
