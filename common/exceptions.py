"""Domain exceptions raised by services and translated into form/user errors by views."""


class ServiceError(Exception):
    """A recoverable domain rule violation with a user-facing message."""


class AuthorizationError(ServiceError):
    """The actor is not allowed to perform this mutation."""


class ConflictError(ServiceError):
    """The mutation conflicts with existing data or business state."""
