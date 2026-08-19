class SciDocError(Exception):
    """Base domain error."""


class InvalidPdfError(SciDocError):
    pass


class EngineUnavailableError(SciDocError):
    pass


class DeterministicProcessingError(SciDocError):
    pass


class StorageSecurityError(SciDocError):
    pass
