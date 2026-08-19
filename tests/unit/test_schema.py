import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from scidoc_core.confidence import ConfidenceState
from scidoc_core.provenance import Provenance
from scidoc_schema.models import (
    DocumentInfo,
    ElementContent,
    ElementType,
    SdrDocument,
    SdrElement,
    SdrPage,
)


def test_sdr_validates_against_language_neutral_schema() -> None:
    sdr = SdrDocument(
        document=DocumentInfo(id="doc_test", filename="sample.pdf", sha256="a" * 64, page_count=1),
        pages=[
            SdrPage(
                number=1,
                width=612,
                height=792,
                classification="native",
                elements=[
                    SdrElement(
                        id="doc_test-p1-e1",
                        type=ElementType.BRAILLE,
                        bbox=(10, 20, 100, 50),
                        reading_order=0,
                        content=ElementContent(
                            text="⠠⠓⠑⠇⠇⠕",
                            unicode="⠠⠓⠑⠇⠇⠕",
                            alt_text="Uncontracted Braille transcription: Hello",
                        ),
                        confidence=1,
                        confidence_source="deterministic_native_pdf",
                        provenance=Provenance(method="native_pdf", engine="pymupdf", source_page=1),
                        review_status=ConfidenceState.ACCEPTED,
                    )
                ],
            )
        ],
        config_hash="b" * 64,
    )
    schema = json.loads(Path("packages/schema/jsonschema/sdr.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        sdr.model_dump(mode="json")
    )
