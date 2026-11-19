import json
import os
import sys
import tempfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

import rag

CORPUS = rag.ROOT / "corpus"
SUPPORTED = {".txt", ".md", ".pdf", ".docx"}


def split_text(text, size=1200, overlap=200):
    text = " ".join(text.split())
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        yield text[start:end]
        if end == len(text):
            break
        start = end - overlap


def extract(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        for page_number, page in enumerate(PdfReader(path).pages, 1):
            yield page_number, page.extract_text() or ""
    elif suffix == ".docx":
        yield None, "\n".join(paragraph.text for paragraph in Document(path).paragraphs)
    else:
        yield None, path.read_text(encoding="utf-8")


def build_index():
    paths = sorted(path for path in CORPUS.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED)
    if not paths:
        raise rag.RagError("No hay documentos compatibles en corpus.")
    chunks = []
    for path in paths:
        try:
            count = 0
            for page, text in extract(path):
                for fragment in split_text(text):
                    chunks.append({"source": path.relative_to(CORPUS).as_posix(), "page": page, "text": fragment})
                    count += 1
            if not count:
                raise rag.RagError(f"No se pudo extraer texto de {path.name}.")
        except rag.RagError:
            raise
        except Exception as exc:
            raise rag.RagError(f"No se pudo procesar {path.name}: {exc}") from exc
    for start in range(0, len(chunks), 16):
        batch = chunks[start:start + 16]
        vectors = rag.embed([chunk["text"] for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            chunk["vector"] = vector
    rag.INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=rag.INDEX_PATH.parent, delete=False) as file:
            temp_name = file.name
            json.dump({"model": rag.EMBED_MODEL, "chunks": chunks}, file, ensure_ascii=False)
        os.replace(temp_name, rag.INDEX_PATH)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Índice creado: {len(paths)} documentos, {len(chunks)} fragmentos.")


if __name__ == "__main__":
    try:
        build_index()
    except (rag.RagError, OSError) as exc:
        print(f"Error de ingesta: {exc}", file=sys.stderr)
        sys.exit(1)
