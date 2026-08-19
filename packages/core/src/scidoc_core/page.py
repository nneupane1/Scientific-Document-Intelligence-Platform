from enum import StrEnum


class PageClassification(StrEnum):
    NATIVE = "native"
    RASTER = "raster"
    HYBRID = "hybrid"
    VECTOR_HEAVY = "vector_heavy"
    UNKNOWN = "unknown"
