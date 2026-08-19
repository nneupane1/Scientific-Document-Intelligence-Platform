from scidoc_core.page import PageClassification
from scidoc_pdf.classifier import classify_page


def test_page_classification_heuristics() -> None:
    assert (
        classify_page(text_coverage=0.4, image_coverage=0, text_blocks=8, vector_objects=2)
        is PageClassification.NATIVE
    )
    assert (
        classify_page(text_coverage=0, image_coverage=0.9, text_blocks=0, vector_objects=0)
        is PageClassification.RASTER
    )
    assert (
        classify_page(text_coverage=0.25, image_coverage=0.2, text_blocks=5, vector_objects=10)
        is PageClassification.HYBRID
    )
    assert (
        classify_page(text_coverage=0, image_coverage=0, text_blocks=0, vector_objects=400)
        is PageClassification.VECTOR_HEAVY
    )
