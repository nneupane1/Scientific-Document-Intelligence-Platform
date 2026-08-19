from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import pymupdf as fitz

from scidoc_core.errors import InvalidPdfError

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = unicodedata.normalize("NFKC", name).replace("\x00", "")
    name = _SAFE_FILENAME.sub("_", name).strip(" .")
    if not name:
        name = "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:180]


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_pdf(path: str | Path) -> int:
    target = Path(path)
    if target.suffix.lower() != ".pdf":
        raise InvalidPdfError("only PDF files are accepted")
    header = target.read_bytes()[:8]
    if not header.startswith(b"%PDF-"):
        raise InvalidPdfError("file does not have a valid PDF signature")
    try:
        with fitz.open(target) as document:
            if document.is_encrypted and not document.authenticate(""):
                raise InvalidPdfError("password-protected PDFs are not supported")
            if document.page_count < 1:
                raise InvalidPdfError("PDF has no pages")
            return int(document.page_count)
    except InvalidPdfError:
        raise
    except Exception as exc:
        raise InvalidPdfError(f"PDF parser rejected the file: {exc}") from exc
