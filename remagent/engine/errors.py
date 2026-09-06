"""
Error types for the dream synthesis engine.

Kept dependency-free so the provider layer, the prompt/parser layer, the
synthesizer, and the CLI can all share them without import cycles.
"""


class DreamSynthesisError(RuntimeError):
    """
    Raised when the LLM consolidation call fails for any reason (missing API
    key, transport error, schema rejection, unparseable response).
    A failed dream must never look like a successful one: callers must let this
    propagate and must not persist any state derived from the failed run.
    """


class ProviderConfigError(DreamSynthesisError):
    """The LLM provider could not be selected or constructed from the environment."""


class NoProviderKeyError(ProviderConfigError):
    """No usable API key was found for any supported provider."""


class ProviderNotInstalledError(ProviderConfigError):
    """The selected provider's SDK extra is not installed."""
