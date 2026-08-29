import xml.etree.ElementTree as ET
from pathlib import Path

def get_namespace(root):
    """Estrae il namespace dal tag root se presente."""
    if '}' in root.tag:
        return root.tag.split('}')[0] + '}'
    return ''

def resolve_tei_path(path, filename):
    base_path = Path(path)
    tei_path = base_path / f"{filename}.tei.xml"
    if tei_path.exists():
        return tei_path

    xml_path = base_path / f"{filename}.xml"
    if xml_path.exists():
        return xml_path

    return xml_path


def normalize_line_id(line_id, line_offsets):
    if not line_id:
        return line_id

    parts = line_id.split("_")
    if len(parts) < 3:
        return line_id

    prefix = "_".join(parts[:2])
    try:
        suffix = int(parts[2])
    except ValueError:
        return line_id

    if prefix not in line_offsets:
        line_offsets[prefix] = 1 if suffix == 0 else 0

    return f"{parts[0]}_{parts[1]}_{suffix + line_offsets[prefix]}"

def tei_to_json(root):
    """Estrae il testo da un root TEI come sequenza ordinata di righe JSON."""
    ns = get_namespace(root)
    
    text_rows = []
    word_id = 0
    
    # Processa il titolo
    head = root.find(f".//{ns}body/{ns}head")
    if head is not None and head.text:
        title_words = [
            {"word": word, "ID": word_id + i}
            for i, word in enumerate((head.text or "").split())
        ]
        if title_words:
            text_rows.append({"type": "titleText", "text": title_words})
            word_id += len(title_words)
    
    # Processa tutte le parole in ordine gerarchico
    for div in root.findall(f".//{ns}div"):
        # Titolo del capitolo
        div_title = div.get("n", "").split()
        if div_title:
            title_words = [
                {"word": word, "ID": word_id + i}
                for i, word in enumerate(div_title)
            ]
            text_rows.append({"type": "chapterTitle", "text": title_words})
            word_id += len(title_words)
        
        # Processa tutte le clausole
        line_offsets = {}
        for cl_or_l in div.findall(f".//{ns}cl") + div.findall(f".//{ns}l"):
            words = []
            for w in cl_or_l.findall(f"{ns}w"):
                if w.text:
                    word_text = w.text + (w.tail.strip() if w.tail else "")
                    for item in word_text.split():
                        words.append({"word": item, "ID": word_id})
                        word_id += 1
            
            if words:
                text_rows.append({
                    "id": normalize_line_id(cl_or_l.attrib.get("id"), line_offsets),
                    "type": "text",
                    "text": words
                })
    
    return text_rows


def tei_to_index_json(path, filename):
    """Costruisce la struttura indice (start/end per ogni blocco) a partire dal JSON di tei_to_json."""
    xml_path = resolve_tei_path(path, filename)
    tree = ET.parse(xml_path)
    text_rows = tei_to_json(tree.getroot())

    content = []
    max_index = 0

    for row in text_rows:
        words = row["text"]
        if not words:
            continue
        start = words[0]["ID"]
        end = words[-1]["ID"] + 1
        content.append({"start": start, "end": end})
        max_index = max(max_index, end)

    return {
        "content": content,
        "maxIndex": max_index
    }


def plain_text_to_rows(filename:str,text: str) -> list[dict]:
    rows = []
    word_id = 0
    
    spl=filename.split()
    title_words=[{"word": word, "ID": word_id + i} for i, word in enumerate(spl)]
    word_id += len(spl)

    rows.append({
        "type": "titleText",
        "text": title_words,
    })


    rows.append({
        "type": "chapterTitle",
        "text": [{"word":1,"ID":word_id}],
    })
    word_id += 1

    chapter_number=1
    line_number=1
    for _, line in enumerate(text.splitlines(), start=1):
        words = line.split()
        if not words:
            chapter_number+=1
            rows.append({
                "type": "chapterTitle",
                "text": [{"word":chapter_number,"ID":word_id}],
            })
            word_id += 1
            line_number=1
            continue

        row_words = [{"word": word, "ID": word_id + i} for i, word in enumerate(words)]
        word_id += len(row_words)

        rows.append({
            "id": f"{chapter_number}_{line_number}_1",
            "type": "text",
            "text": row_words,
        })
        line_number+=1

    return rows

#------------------------------------------------------------------------------------------------------------

def calculate_chapter_index(text: list[dict]) -> list[dict]:
    """Estrae l'indice dei capitoli (titolo + range di righe) da un array di righe JSON."""
    result: list[dict] = []
    for line_index, line in enumerate(text):
        if line["type"] == "chapterTitle":
            chapter_title = "".join(f"{word['word']} " for word in line["text"])
            if result:
                result[-1]["indexMax"] = line_index
            result.append({
                "value": chapter_title,
                "indexMin": line_index,
                "indexMax": len(text),
            })
    return result


def convert_tei(textInfo):
    "Convert TEI file into plain-text JSON compatible for frontend rendering"
    if hasattr(textInfo, 'path') and hasattr(textInfo, 'filename'):
        path = textInfo.path
        filename = textInfo.filename
    elif isinstance(textInfo, (tuple, list)) and len(textInfo) >= 2:
        path, filename = textInfo[0], textInfo[1]
    else:
        raise TypeError('textInfo must provide path and filename')

    xml_path = resolve_tei_path(path, filename)
    tree = ET.parse(xml_path)
    text = tei_to_json(tree.getroot())

    return text

def convert_tei_upload(text):
    source = text.file if hasattr(text, "file") else text
    tree = ET.parse(source)
    return tei_to_json(tree.getroot())