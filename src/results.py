from typing import Any

import hashlib
from urllib.parse import quote_plus

import pandas as pd  # type: ignore
from openpyxl.styles import Alignment, Font  # type: ignore
from io import BytesIO

from settings import static_path, base_url, FRONTEND_URL


pfa_templ = "{path}/{fname}#{addr}"
# fname_templ = "/results/{params}.xlsx"
fname_templ = "/results/{method}-{sources}-{params}.xlsx"
# fname_templ = "/results/{query}-{method}-{params}.xlsx"

table_templ = """<table class="results">{body}</table>"""
trow_templ = """<tr><td class="quote">{text}</td><td class="info"><span title="accuracy" style="font-size: large; opacity: {acc}">{acc}</span><br><a href="{href}" title="{urn}" target="fulltext">{ref}<br><span style="font-weight: bold; color: {color}">[{src}]</span></a></td></tr>"""

href_templ = """<a href="{href}" target="fulltext">{label}</a>"""
entry_templ = """<li>{link} [{accuarcy:.4f}]:<br/><span class="lg">{text}</span></li>"""

export_templ = """<a href="{url}">[Export Results]</a>"""

from settings import ms2color


def urn2path(s: str) -> str:
    """
    >>> urn2path("syntacticus.gospel.zographensis.marco:4.19")
    'syntacticus.gospel.zographensis/marco.tei.xml#4_19'
    >>> urn2path("oxford.psalter.bologna.BM8:112.7")
    'oxford.psalter.bologna/BM8.tei.xml#112_7'
    >>> urn2path("syntacticus.psalter.sinai.psal-sin:10.30")
    'syntacticus.psalter.sinai/psal-sin.tei.xml#10_30'
    """
    last = s.rfind(".")
    prev = s.rfind(".", 0, last)
    return (
        f"""{s[:prev]}/{s[prev + 1 : last].replace(":", ".tei.xml#")}_{s[last + 1 :]}"""
    )


def path2urn(s: str) -> str:
    """
    >>> path2urn("syntacticus.gospel.zographensis/marco.tei.xml#4_19")
    'syntacticus.gospel.zographensis.marco:4.19'
    >>> path2urn("oxford.psalter.bologna/BM8.tei.xml#112_7")
    'oxford.psalter.bologna.BM8:112.7'
    >>> path2urn("syntacticus.psalter.sinai/psal-sin.tei.xml#10_30")
    'syntacticus.psalter.sinai.psal-sin:10.30'
    """
    return s.replace(".tei.xml#", ":").replace("_", ".").replace("/", ".")


def path2source(s) -> str:
    return path2urn(s).split(":")[0]


def path2link(s: str) -> str:
    return f"{static_path}{s.replace('.tei.xml', '.html')}"


def path2url(s: str) -> str:
    return f"{base_url}{static_path}{s.replace('.tei.xml', '.html')}"


def path2loc(s: str) -> str:
    """
    >>> path2loc("syntacticus.gospel.zographensis./marco.tei.xml#4_19")
    'marco 4.19'
    >>> path2loc("oxford.psalter.bologna/BM8.tei.xml#112_7")
    'BM8 112.7'
    >>> path2loc("syntacticus.psalter.sinai/psal-sin.tei.xml#10_30")
    'psal-sin 10.30'
    """
    return s.split("/")[-1].replace(".tei.xml#", " ").replace("_", ".")


def source2ms(s: str) -> str:
    """
    >>> path2ms("syntacticus.gospel.zographensis")
    'Z'
    >>> path2ms("syntacticus.gospel.marianus")
    'M'
    >>> path2ms("oxford.psalter.bologna")
    'B'
    >>> path2ms("syntacticus.psalter.sinai")
    'S'
    >>> path2ms("syntacticus.gospel.vulgate")
    'V'
    """
    return s.split(".")[2][0].upper()


def sources2code(sources: list[str]) -> str:
    """
    >>> sources2code(["syntacticus.gospel.zographensis", "syntacticus.gospel.marianus"])
    'MZ'
    >>> sources2code(["oxford.psalter.bologna", "syntacticus.psalter.sinai"])
    'BS'
    """
    codes = [source2ms(s) for s in sources]
    codes.sort()
    return "".join(codes)


def path2ms(s: str) -> str:
    """
    >>> path2ms("syntacticus.gospel.zographensis/marco.tei.xml#4_19")
    'Z'
    >>> path2ms("syntacticus.gospel.marianus/marco.tei.xml#4_19")
    'M'
    >>> path2ms("oxford.psalter.bologna/BM8.tei.xml#112_7")
    'B'
    >>> path2ms("syntacticus.psalter.sinai/psal-sin.tei.xml#10_30")
    'S'
    """
    return source2ms(s.split("/")[0])


def build_fname(params: dict[str, str]) -> str:
    """
    >>> params = {"query": "hello", "method": "regex", "sources":"BMSZ"}
    >>> build_fname(params)
    '/results/regex-BMSZ-452b6711460846e87367c2fcee2ea493.xlsx'
    >>> build_fname(params)
    '/results/regex-BMSZ-452b6711460846e87367c2fcee2ea493.xlsx'
    """

    m = hashlib.md5()
    for s in params.values():
        m.update(str(s).encode())

    return fname_templ.format(
        # query=quote_plus(params["query"][:20]),
        method=params["method"],
        sources=params["sources"],
        params=m.hexdigest(),
    )


def render_from_export(fname: str) -> tuple[str, str]:
    df = pd.read_excel(fname)

    html_rows = []
    for i, row in df.iterrows():
        text = row["found"]
        addr = urn2path(row["location"])
        acc = float(row["similarity"])
        html_rows += [
            trow_templ.format(
                text=text,
                acc="1.0" if acc == 1 else f"{acc:0.3f}",
                href=path2link(addr),
                ref=path2loc(addr),
                color=ms2color[path2ms(addr)],
                src=path2ms(addr),
                urn=path2urn(addr),
            )
        ]
    html_result = table_templ.format(body="\n".join(html_rows))

    return export_templ.format(url=base_url + fname), html_result


def render_excel(
    params: dict[str, str],
    data: list[tuple[str, str, float]],
) -> str:
    result = [
        {
            "found": d[0],
            "similarity": f"{d[2]:0.4f}",
            "location": path2loc(d[1]),
            "source": path2source(d[1]),
            "url": path2url(d[1]),
            "urn": path2urn(d[1]),
        }
        for d in data
    ]
    df = pd.DataFrame(result)

    for k, v in params.items():
        df[k] = v

    col = df.pop("query")
    df.insert(0, "query", col)

    fname_result = build_fname(params)
    with pd.ExcelWriter(fname_result) as writer:
        df.to_excel(writer, index=False, sheet_name="Result")
        wb = writer.book
        font = Font(name="BukyVede")
        align = Alignment(wrap_text=True)
        ws = wb.worksheets[0]

        first = True
        for cell in ws["A"]:
            if first:
                first = False
                continue
            cell.font = font
            cell.alignment = align

        first = True
        for cell in ws["B"]:
            if first:
                first = False
                continue
            cell.font = font
            cell.alignment = align

        ws.column_dimensions["A"].width = 60
        ws.column_dimensions["B"].width = 60
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 30
        ws.column_dimensions["E"].width = 40

    return fname_result


def render_html(data: list[tuple[str, str, float]]) -> str:
    html_rows = []
    for text, addr, acc in data:
        html_rows += [
            trow_templ.format(
                text=text,
                acc="1.0" if acc > 0.99 else (f"{acc:.2f}"[1:]),
                href=path2link(addr),
                ref=path2loc(addr).replace(" ", "<br>"),
                color=ms2color[path2ms(addr)],
                src=path2ms(addr),
                urn=path2urn(addr),
            )
        ]
    html_result = table_templ.format(body="\n".join(html_rows))

    return html_result


def render_json(data: list[tuple[str, str, float]]) -> list[dict[str, str]]:
    result = [
        {
            "found": d[0],
            "accuracy": f"{d[2]:0.4f}",
            "location": path2loc(d[1]),
            "source": path2source(d[1]),
            "urn": path2urn(d[1]),
        }
        for d in data
    ]

    return result


def render_table(
    params: dict[str, str],
    data: list[tuple[str, str, float]],
) -> tuple[str, str]:
    """A list of <text, address, accuracy>. Returns path to export and HTML body.
    A precondition is that build_fname(params) does not exist.

    >> params = {"query": "hello", "method": "regex", "sources":"BMSZ"}
    >> data = [("text", "psalter.bologna.oxford", 1)]
    >> render_table(params, data)
    """

    data.sort(key=lambda x: x[2], reverse=True)
    if not data:
        return "Result is empty.", ""

    html_result = render_html(data)
    fname_result = render_excel(params, data)

    return export_templ.format(url=base_url + fname_result), html_result

###

def render_json_hybrid(texts,scores):
    result=[]
    for key in scores.keys():
        s=scores[key]
        result.append({
            "found":texts[key],
            "confidency":s["score"],
            "algos":s["algos"],
            "source": path2source(key),
            "urn": path2urn(key.split("$$")[0]),
        })
    return result

def render_excel_hybrid(
    params: dict[str, str],
    data: list[dict[str, object]],
    urn_b: str | None = None,
    h_start: int | None = None,
    h_end: int | None = None,
) -> bytes:
    df = pd.DataFrame(data)

    for k, v in params.items():
        df[k] = v

    if urn_b is not None and h_start is not None and h_end is not None:
        df["preview_url"] = df["urn"].apply(
            lambda urn_h: f"{FRONTEND_URL}/previewDouble?urn_b={quote_plus(urn_b)}&urn_h={quote_plus(urn_h)}&b_start={h_start}&b_end={h_end}"
        )
    else:
        df["preview_url"] = df.apply(
            lambda row: f"{FRONTEND_URL}/previewSingle?urn_h={quote_plus(str(row['urn']))}&query={quote_plus(str(row['query']))}",
            axis=1,
        )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Result")

        ws = writer.book.worksheets[0]
        ws.column_dimensions["A"].width = 60
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 35
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 40

    return buffer.getvalue()

