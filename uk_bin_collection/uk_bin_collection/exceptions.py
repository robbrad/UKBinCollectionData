"""Domain exceptions raised by the UK Bin Collection core library.

The library deliberately raises these exceptions without importing Home Assistant,
CLI, or API concerns.  Each application boundary can therefore translate the same
failure into an appropriate user-facing result.
"""


class UKBinCollectionError(Exception):
    """Base class for expected UK Bin Collection failures."""


class ConfigurationError(UKBinCollectionError):
    """The supplied collector configuration is invalid or incomplete."""


class InvalidCouncilModuleError(ConfigurationError):
    """The requested council is not present in the installed council registry."""


class DependencyError(UKBinCollectionError):
    """A required runtime dependency cannot be used safely."""


class MissingDependencyError(DependencyError):
    """A required runtime dependency is not installed or is incomplete."""


class DependencyShadowingError(DependencyError):
    """An import resolves outside the files owned by its expected distribution."""


class BrowserUnavailableError(UKBinCollectionError):
    """A Selenium browser session could not be created or reached."""


class AddressMismatchError(UKBinCollectionError):
    """No unique upstream address matches the configured property."""


class UpstreamAccessDenied(UKBinCollectionError):
    """The upstream collection service denied access to the request."""


class SiteChanged(UKBinCollectionError):
    """The upstream site no longer has the structure expected by its adapter."""
