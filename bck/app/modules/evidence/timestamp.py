import hashlib
import hmac
from abc import ABC, abstractmethod
from datetime import UTC, datetime


class TimestampAuthorityHook(ABC):
    """Abstract base class for timestamping evidence."""

    @abstractmethod
    def get_timestamp_token(self, data_hash: str) -> dict:
        """
        Returns a timestamp token for the given data hash.
        Must return a dictionary containing the timestamp and a verification token.
        """
        pass


class LocalRFC3161Hook(TimestampAuthorityHook):
    """
    Local implementation of a timestamp authority.
    Produces deterministic tokens without external network calls.
    """

    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("secret_key is required for LocalRFC3161Hook")
        self._secret_key = secret_key.encode("utf-8")

    def get_timestamp_token(self, data_hash: str) -> dict:
        """
        Generates a UTC ISO-8601 timestamp and a local HMAC-SHA256 token.
        """
        timestamp = datetime.now(UTC).isoformat()

        # Generate a deterministic token based on hash and timestamp
        message = f"{data_hash}:{timestamp}".encode()
        token = hmac.new(self._secret_key, msg=message, digestmod=hashlib.sha256).hexdigest()

        return {"timestamp": timestamp, "token": token, "authority": "LocalRFC3161Hook"}
