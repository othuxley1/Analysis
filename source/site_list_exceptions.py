"""A script for custom exception classes."""

class Error(Exception):
    """Base class for other Exceptions"""
    pass

class DecommissionedError(Error):
    """Raised when a system has been decommissioned."""
    pass



