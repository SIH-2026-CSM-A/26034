"""The evidence module constructs from real settings, and refuses to guess what is unset.

Every object here is built from a validated :class:`~app.core.config.Settings`, the same
object production hands it, and never from a mock. What is asserted is the boundary: an
unstated retention window keeps rather than purges, and an unconfigured store or
timestamp authority names the variable a deployment has to set.
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.evidence import (
    LocalRFC3161Hook,
    LocalStorageClient,
    S3ContentAddressedStorageClient,
)
from app.modules.evidence.chain import create_genesis_entry
from app.modules.evidence.domain import EvidenceAssetType
from app.modules.evidence.retention import RetentionManager

JWT = "test-signing-key-not-used-anywhere-real"
S3 = {
    "evidence_s3_endpoint_url": "http://minio.internal:9000",
    "evidence_s3_bucket": "evidence",
    "evidence_s3_access_key": "pccs",
    "evidence_s3_secret_key": "not-a-real-secret",
}


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, jwt_secret=JWT, **overrides)


def _aged(days: int):
    when = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    return create_genesis_entry("image", when, EvidenceAssetType.PRODUCT_IMAGE)


def test_the_windows_and_the_purge_flag_are_unset_by_default() -> None:
    """No retention period is sourced in the corpus, so none is defaulted here."""
    plain = settings()
    assert plain.evidence_image_retention_days is None
    assert plain.evidence_pii_retention_days is None
    assert plain.evidence_destructive_purge_enabled is False


def test_an_unstated_window_keeps_rather_than_purges(tmp_path) -> None:
    manager = RetentionManager(LocalStorageClient(str(tmp_path)), settings())
    assert manager.should_purge(_aged(10_000), datetime.now(UTC)) is False


def test_the_windows_are_read_from_the_environment(monkeypatch, tmp_path) -> None:
    """The variables a deployment sets, through pydantic-settings, not through a mock."""
    monkeypatch.setenv("JWT_SECRET", JWT)
    monkeypatch.setenv("EVIDENCE_IMAGE_RETENTION_DAYS", "30")
    monkeypatch.setenv("EVIDENCE_PII_RETENTION_DAYS", "7")
    manager = RetentionManager(LocalStorageClient(str(tmp_path)), Settings(_env_file=None))
    now = datetime.now(UTC)
    assert manager.should_purge(_aged(31), now) is True
    assert manager.should_purge(_aged(29), now) is False
    personal = create_genesis_entry(
        "pii", (now - timedelta(days=8)).isoformat(), EvidenceAssetType.PERSONAL_DATA
    )
    assert manager.should_purge(personal, now) is True


def test_a_zero_or_negative_window_is_refused() -> None:
    """Zero would purge everything on the first pass; it is not a window."""
    with pytest.raises(ValidationError):
        settings(evidence_image_retention_days=0)


def test_the_manager_reads_the_process_settings_when_handed_none(monkeypatch, tmp_path) -> None:
    from app.core.config import get_settings

    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("JWT_SECRET", JWT)
    monkeypatch.setenv("EVIDENCE_IMAGE_RETENTION_DAYS", "3")
    get_settings.cache_clear()
    try:
        manager = RetentionManager(LocalStorageClient(str(tmp_path)))
        assert manager.get_retention_days(EvidenceAssetType.PRODUCT_IMAGE) == 3
    finally:
        get_settings.cache_clear()


def test_the_s3_client_constructs_from_settings() -> None:
    client = S3ContentAddressedStorageClient.from_settings(settings(**S3))
    assert client.bucket_name == "evidence"
    assert client.s3.meta.endpoint_url == "http://minio.internal:9000"


@pytest.mark.parametrize("absent", sorted(S3))
def test_a_partly_configured_store_names_what_is_missing(absent: str) -> None:
    partial = {name: value for name, value in S3.items() if name != absent}
    with pytest.raises(LookupError, match=absent.upper()):
        S3ContentAddressedStorageClient.from_settings(settings(**partial))


def test_the_timestamp_hook_constructs_from_settings_and_its_token_verifies() -> None:
    secret = "a-timestamp-key-of-at-least-thirty-two-characters"
    hook = LocalRFC3161Hook.from_settings(settings(evidence_timestamp_secret=secret))
    token = hook.get_timestamp_token("abc123")
    expected = hmac.new(
        secret.encode(), f"abc123:{token['timestamp']}".encode(), hashlib.sha256
    ).hexdigest()
    assert token["token"] == expected


def test_an_unset_timestamp_secret_is_named() -> None:
    with pytest.raises(LookupError, match="EVIDENCE_TIMESTAMP_SECRET"):
        LocalRFC3161Hook.from_settings(settings())


def test_a_short_timestamp_secret_is_refused() -> None:
    with pytest.raises(ValidationError):
        settings(evidence_timestamp_secret="short")
