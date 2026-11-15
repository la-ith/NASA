"""Source adapters (spec v4.0, section 18.3). Each one describes its product, checks coverage, fetches,
validates without changing the original, and normalizes into typed values."""
import hashlib
import json


class AdapterError(Exception):
    """Base class; `code` is the error code the API returns."""

    code = "adapter_error"


class ProviderUnavailable(AdapterError):
    code = "provider_error"


class SourceIntegrityError(AdapterError):
    code = "data_integrity"


class NotCovered(AdapterError):
    code = "not_covered"


def content_hash(raw: object) -> str:
    """SHA-256 of the canonical JSON form; checks local integrity, not scientific validity (section 18.4)."""
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
