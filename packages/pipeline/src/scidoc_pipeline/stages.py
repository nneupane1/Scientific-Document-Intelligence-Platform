from enum import StrEnum


class PipelineStage(StrEnum):
    INGEST = "ingest"
    INSPECT = "inspect"
    PROCESS_PAGE = "process_page"
    AGGREGATE = "aggregate"
    VALIDATE = "validate"
    EXPORT = "export"
    COMPLETE = "complete"
