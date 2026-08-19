from pathlib import Path

import pymupdf as fitz
from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw
from scidoc_core.config import Settings
from scidoc_database.models import Job
from scidoc_database.session import configure_database, create_schema, session_scope
from scidoc_pipeline.document_pipeline import DocumentPipeline


def test_native_pdf_to_persisted_sdr(tiny_pdf: Path, tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
    )
    configure_database(settings.database_url)
    create_schema()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        ingest = pipeline.ingest(tiny_pdf)
        sdr = pipeline.process(ingest.document_id, ingest.job_id)
        assert sdr.document.page_count == 1
        assert sdr.pages[0].classification == "native"
        assert any(
            "Scientific document intelligence" in (element.content.text or "")
            for element in sdr.pages[0].elements
        )
        assert sdr.processing.ocr_elements == 0
        schema = __import__("json").loads(
            Path("packages/schema/jsonschema/sdr.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(sdr.model_dump(mode="json"))
        assert (
            settings.storage_root
            / "documents"
            / ingest.document_id
            / "results"
            / "document.sdr.json"
        ).exists()


def test_exact_duplicate_reuses_document(tiny_pdf: Path, tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'duplicate.db'}", storage_root=tmp_path / "data"
    )
    configure_database(settings.database_url)
    create_schema()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        first = pipeline.ingest(tiny_pdf)
        second = pipeline.ingest(tiny_pdf)
        assert first.document_id == second.document_id
        assert second.duplicate


def test_duplicate_is_reprocessed_when_processing_configuration_changes(
    tiny_pdf: Path, tmp_path: Path
) -> None:
    database_url = f"sqlite:///{tmp_path / 'reconfigure.db'}"
    storage_root = tmp_path / "data"
    settings = Settings(database_url=database_url, storage_root=storage_root)
    configure_database(settings.database_url)
    create_schema()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        first = pipeline.ingest(tiny_pdf)
        pipeline.process(first.document_id, first.job_id)

        changed_pipeline = DocumentPipeline(
            session,
            Settings(
                database_url=database_url,
                storage_root=storage_root,
                enable_charts=False,
            ),
        )
        duplicate = changed_pipeline.ingest(tiny_pdf)
        persisted_job = session.get(Job, duplicate.job_id)

    assert duplicate.duplicate
    assert duplicate.document_id == first.document_id
    assert duplicate.job_id != first.job_id
    assert persisted_job is not None


def test_supplied_formula_pdf_routes_embedded_formulas(tmp_path: Path) -> None:
    source = Path("benchmark/datasets/source-documents/input/Formula.pdf")
    if not source.exists():
        __import__("pytest").skip("canonical corpus has not been extracted")
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'formula.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
    )
    configure_database(settings.database_url)
    create_schema()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        ingest = pipeline.ingest(source)
        sdr = pipeline.process(ingest.document_id, ingest.job_id)
        equations = [
            element for element in sdr.pages[0].elements if element.type.value == "equation"
        ]
        assert len(equations) >= 2
        assert any(
            element.provenance.method in {"formula_recognition", "formula_ocr_fallback"}
            for element in equations
        )


def test_tables_charts_and_chemistry_are_emitted_as_structured_elements(tmp_path: Path) -> None:
    source = tmp_path / "mixed-scientific-content.pdf"
    chart_path = tmp_path / "chart.png"
    chart = Image.new("RGB", (600, 320), "white")
    drawing = ImageDraw.Draw(chart)
    drawing.line((60, 270, 540, 270), fill="black", width=3)
    drawing.line((60, 270, 60, 35), fill="black", width=3)
    drawing.line((80, 240, 210, 170, 360, 210, 520, 70), fill="#527f79", width=8)
    drawing.text((75, 15), "Measured response", fill="black")
    chart.save(chart_path)

    document = fitz.open()
    table_page = document.new_page(width=400, height=300)
    for x in (50, 150, 250, 350):
        table_page.draw_line((x, 50), (x, 170), color=(0, 0, 0))
    for y in (50, 90, 130, 170):
        table_page.draw_line((50, y), (350, y), color=(0, 0, 0))
    values = [
        ["Name", "Value", "Unit"],
        ["Mass", "12", "kg"],
        ["Speed", "4", "m/s"],
    ]
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            table_page.insert_text(
                (60 + column_index * 100, 75 + row_index * 40), value, fontsize=10
            )
    table_page.insert_text((50, 215), "2 H2 + O2 -> 2 H2O", fontsize=12)

    chart_page = document.new_page(width=400, height=300)
    chart_page.insert_text((50, 35), "Figure 1. Chart of measured response", fontsize=11)
    chart_page.insert_image(fitz.Rect(50, 55, 350, 215), filename=str(chart_path))
    document.save(source)
    document.close()

    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'mixed.db'}",
        storage_root=tmp_path / "data",
        queue_mode="synchronous",
    )
    configure_database(settings.database_url)
    create_schema()
    with session_scope() as session:
        pipeline = DocumentPipeline(session, settings)
        ingest = pipeline.ingest(source)
        sdr = pipeline.process(ingest.document_id, ingest.job_id)

    table = next(element for element in sdr.pages[0].elements if element.type.value == "table")
    assert table.content.columns == ["Name", "Value", "Unit"]
    assert table.content.rows == [["Mass", "12", "kg"], ["Speed", "4", "m/s"]]
    assert table.provenance.method == "native_pdf_table"
    assert any(element.type.value == "chemical_equation" for element in sdr.pages[0].elements)
    chart_element = next(
        element for element in sdr.pages[1].elements if element.type.value == "chart"
    )
    assert chart_element.content.alt_text
    assert chart_element.bbox == (50.0, 55.0, 350.0, 215.0)


def test_all_scientific_domains_are_enabled_by_default() -> None:
    settings = Settings()
    assert settings.enable_tables
    assert settings.enable_chemistry
    assert settings.enable_diagrams
    assert settings.enable_charts
    assert settings.enable_vlm
