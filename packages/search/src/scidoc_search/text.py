from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from scidoc_schema.models import SdrDocument

from scidoc_search.math import normalize_math_query
from scidoc_search.normalization import normalize_text


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int
    element_id: str
    element_type: str
    snippet: str
    bbox: tuple[float, float, float, float]


def search_document(sdr: SdrDocument, query: str) -> list[SearchHit]:
    text_query = normalize_text(query)
    math_query = normalize_math_query(query)
    hits: list[SearchHit] = []
    for page in sdr.pages:
        for element in page.elements:
            text = element.content.text or ""
            latex = element.content.normalized_latex or element.content.latex or ""
            if (text_query and text_query in normalize_text(text)) or (
                math_query and math_query in normalize_math_query(latex)
            ):
                source = text or latex
                hits.append(
                    SearchHit(
                        page_number=page.number,
                        element_id=element.id,
                        element_type=element.type.value,
                        snippet=source[:240],
                        bbox=element.bbox,
                    )
                )
    return hits
