from pathlib import Path
from zipfile import ZipFile


def test_canonical_zip_contains_expected_source_documents() -> None:
    archive = Path("source-documents.zip")
    assert archive.exists()
    with ZipFile(archive) as source:
        names = set(source.namelist())
    assert "input/Formula.pdf" in names
    assert "input/What is sugar.pdf" in names
    assert not any("physics" in name.casefold() for name in names)
