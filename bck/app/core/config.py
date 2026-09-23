"""One place for everything the deployment decides rather than the code.

Two things here are load-bearing beyond ordinary settings:

**Designations.** ``role_designations`` maps the three structural tiers to the titles a
particular state actually uses. The tiers are fixed; the words are not. Every officer-
facing string comes through :meth:`Settings.designation`, so a deployment swaps the
nomenclature by setting one environment variable and no permission check changes
behaviour.

**Cost ceilings.** ``AGENTS.md``: *never call a paid API without the cost ceiling in
``core/config.py`` in the loop*. One mapping, read by provider name, so a provider's
budget is a deployment decision in one file rather than a constant in whichever module
happens to call something paid. Cloud OCR sits at ``0`` by default — off is the default
state, and turning it on is a deliberate edit to configuration.

Settings are read from the environment (see ``bck/.env.example``). Nothing here has a
default that would be dangerous if a deployment forgot to set it: ``jwt_secret`` has no
default at all, so a missing key fails at startup rather than shipping a guessable one.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.contracts import ContractModel, EvidenceProvider
from app.core.rbac import Jurisdiction, RoleTier

DEFAULT_ROLE_DESIGNATIONS: dict[RoleTier, str] = {
    RoleTier.STATE: "Controller of Legal Metrology",
    RoleTier.REGIONAL: "Deputy Controller of Legal Metrology",
    RoleTier.DISTRICT: "Legal Metrology Inspector",
}
"""The designations used when a deployment sets none.

A starting point, not a fact about any particular state. States differ — "Assistant
Controller" for the regional tier, a "Commissioner" at the top — and the pilot state is
not chosen. Override with the ``ROLE_DESIGNATIONS`` environment variable.
"""


class OfficerCredential(ContractModel):
    """One officer's login, as a deployment configures it.

    Credentials are configuration until there is a users table to hold them. The password
    is stored only as a bcrypt hash — see :func:`app.core.auth.hash_password`, which is
    how an administrator produces one.
    """

    username: str = Field(min_length=1)
    """The username typed at the login form."""

    password_hash: str = Field(min_length=1)
    """A bcrypt hash. Never a password."""

    tier: RoleTier
    """Which structural tier this officer holds."""

    jurisdiction: Jurisdiction
    """The territory they may see, filled to the depth their tier requires."""

    read_only: bool = False
    """A demonstration login. It may read and may start a scan, and nothing else that
    writes — see :data:`app.core.auth.READ_ONLY_WRITES`. It cannot finalise a review or move
    a complaint, so seeded threads survive every visitor who signs in with it. An officer in
    :data:`app.core.auth.PUBLISHED_OFFICERS` is read-only regardless of this flag."""


class Settings(BaseSettings):
    """Deployment configuration, read from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    """SQLAlchemy URL, also read by Alembic. ``None`` until a deployment sets it."""

    api_host: str = "127.0.0.1"
    """Interface uvicorn binds to."""

    api_port: int = 8000
    """Port uvicorn binds to."""

    cors_allowed_origins: str = "http://localhost:5173"
    """Comma-separated origins allowed to call the API from a browser."""

    log_level: str = "INFO"
    """Root log level: DEBUG, INFO, WARNING or ERROR."""

    datasets_dir: Path | None = None
    """Directory holding local image and label data. See ``datasets/README.md``."""

    rules_corpus_dir: Path | None = None
    """Directory holding the rules corpus. See ``rules-corpus/README.md``."""

    pdp_weights_path: Path | None = None
    """YOLO weights for principal-display-panel detection.

    Optional. ``None`` by default and deliberately NOT part of the startup check: there is
    no PDP-trained detector, and pointing this at stock COCO weights is worse than leaving
    it unset, because ``detect_pdp`` returns a box from whatever the detector hands back and
    that area feeds the Rule 7 Table-I band lookup. Unset, detection falls back to a
    heuristic region that is a distinct type, so a heuristic panel can never be mistaken for
    a model detection. The three OCR paths remain required at boot: they are pre-cached, and
    the honest place to find a fresh clone missing them is boot, not an officer's first scan.
    """

    ocr_det_model_dir: Path | None = None
    """PaddleOCR text-detection model directory. Explicit and local, so nothing downloads
    a model mid-scan — the demo has to survive the venue network failing."""

    ocr_rec_model_dir: Path | None = None
    """PaddleOCR text-recognition model directory. Same reasoning as the detector."""

    tesseract_tessdata_dir: Path | None = None
    """Tesseract's ``tessdata`` directory, for the constrained re-read of MRP and net
    quantity.

    A fourth model path rather than a Tesseract detail. ``extract_mrp_quantity`` raises
    ``FileNotFoundError`` without it, and the second pass exists because an 8 read as a B
    is tolerable on an address and not on a price — so a deployment missing this is one
    that would silently do without the check that protects the two declarations most worth
    protecting. Checked at startup with the other three.
    """

    capture_store_dir: Path | None = Path("storage/captures")
    """Where an officer's uploaded capture is held, content-addressed, after submission.

    Held so a scan can be evaluated again once the officer confirms its product category —
    the category proposal only exists after the first evaluation, so the confirmation can
    only come after it, and re-evaluating needs the photograph. Blank turns holding off:
    scans still evaluate, and a later category confirmation is refused with a 409 that says
    the capture is not held. Consumer uploads are never held; nobody confirms a category
    for one, and an unauthenticated route must not be a way to fill a disk.
    """

    jwt_secret: str = Field(min_length=32)
    """Signing key for access tokens. Required — there is deliberately no default, and a
    key shorter than the SHA-256 block that signs with it is refused."""

    jwt_algorithm: str = "HS256"
    """Signing algorithm. Passed as an explicit allowlist when decoding, so a token
    presenting any other algorithm — ``none`` above all — is rejected."""

    access_token_ttl_minutes: int = Field(default=60, gt=0)
    """How long an issued access token stays valid."""

    role_designations: dict[RoleTier, str] = DEFAULT_ROLE_DESIGNATIONS
    """Tier to the designation this deployment's state uses for it."""

    cost_ceilings: dict[str, Decimal] = {EvidenceProvider.CLOUD_OCR.value: Decimal("0")}
    """Provider name to its spending ceiling. ``Decimal`` because it is money."""

    consumer_scans_per_client_per_minute: int = Field(default=3, gt=0)
    """Consumer image uploads one client address may submit in a minute. The route has no
    login, and each accepted upload is an OCR run of the better part of a minute."""

    consumer_scans_per_minute: int = Field(default=12, gt=0)
    """Consumer image uploads accepted in a minute from all clients together. The client
    address is a header behind a proxy, so the per-client limit alone can be walked round."""

    consumer_scans_max_pending: int = Field(default=5, gt=0)
    """Consumer evaluations that may be queued or running at once. Evaluation is serialised
    and each queued scan holds a decoded frame in memory, so the queue itself is bounded:
    past this the upload is refused with a 429 rather than accepted into a growing backlog."""

    officers: tuple[OfficerCredential, ...] = ()
    """Officers who may log in. Empty by default: a deployment that configures none has
    no accounts, rather than a default account somebody forgets to remove."""

    evidence_image_retention_days: int | None = Field(default=None, gt=0)
    """Days a stored product image is kept before it is eligible for purge.

    No default, deliberately. No retention period for evidence is sourced anywhere in
    ``rules-corpus/``, and a number written here would be an invented one. Unset, nothing
    expires: :class:`~app.modules.evidence.retention.RetentionManager` treats an absent
    window as "keep", never as zero."""

    evidence_pii_retention_days: int | None = Field(default=None, gt=0)
    """Days personal data held as evidence is kept. Same terms as the image window: unset
    means nothing expires, and the figure is a deployment's to state."""

    evidence_destructive_purge_enabled: bool = False
    """Whether an expired asset is actually deleted from storage. Off by default: with it
    off, the retention manager reports what it would purge and touches nothing."""

    evidence_s3_endpoint_url: str | None = None
    """S3-compatible endpoint for content-addressed evidence storage (MinIO in
    ``docker-compose.prod.yml``). Unset means the local capture store only."""

    evidence_s3_bucket: str | None = None
    """The bucket evidence objects are written to."""

    evidence_s3_access_key: str | None = None
    """Access key for the evidence bucket."""

    evidence_s3_secret_key: str | None = None
    """Secret key for the evidence bucket. Never logged."""

    evidence_timestamp_secret: str | None = Field(default=None, min_length=32)
    """HMAC key for :class:`~app.modules.evidence.timestamp.LocalRFC3161Hook`. No default:
    a timestamp token signed with a key anybody can read from a repository attests to
    nothing. Held apart from ``jwt_secret`` so rotating one does not invalidate the other."""

    @field_validator(
        "datasets_dir",
        "rules_corpus_dir",
        "pdp_weights_path",
        "ocr_det_model_dir",
        "ocr_rec_model_dir",
        "tesseract_tessdata_dir",
        "capture_store_dir",
        mode="before",
    )
    @classmethod
    def _blank_path_is_unset(cls, value: Any) -> Any:
        """Treat ``DATASETS_DIR=`` as unset rather than as the current directory."""
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _every_tier_has_a_designation(self) -> "Settings":
        """Reject a partial ``ROLE_DESIGNATIONS``.

        A deployment that names two of the three tiers would otherwise fail at whichever
        request first needed the third.
        """
        missing = [tier.name for tier in RoleTier if tier not in self.role_designations]
        if missing:
            raise ValueError(
                f"role_designations is missing a designation for: {', '.join(missing)}"
            )
        return self

    @property
    def cors_origins(self) -> tuple[str, ...]:
        """``cors_allowed_origins`` split into the list Starlette's middleware wants."""
        return tuple(
            origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()
        )

    def designation(self, tier: RoleTier) -> str:
        """This deployment's title for ``tier``.

        The only way to turn a tier into words. Nothing else in the codebase spells a
        designation out.
        """
        return self.role_designations[tier]

    def missing_model_paths(self) -> tuple[str, ...]:
        """Settings whose model file or directory is unset or absent on disk.

        Read once at startup, never per request. A vision stage that cannot run must stop
        the application starting: surfacing it as a 500 on the first scan turns a missing
        file into a failure in front of whoever is watching, and a fallback would turn it
        into a verdict produced by a path nobody chose.

        Returns the *setting names*, not the paths, because the message a deployment needs
        is which environment variable to set.
        """
        missing: list[str] = []
        for name in (
            "ocr_det_model_dir",
            "ocr_rec_model_dir",
            "tesseract_tessdata_dir",
        ):
            path = getattr(self, name)
            if path is None or not path.exists():
                missing.append(name)
        return tuple(missing)

    def cost_ceiling(self, provider: str) -> Decimal:
        """The spending ceiling for ``provider``.

        Raises rather than returning a permissive default: a provider nobody has budgeted
        for is a configuration gap, and a call that fires anyway is the failure this
        ceiling exists to prevent.
        """
        try:
            return self.cost_ceilings[provider]
        except KeyError:
            raise LookupError(
                f"no cost ceiling configured for provider {provider!r}; "
                f"add it to COST_CEILINGS before calling it"
            ) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide settings, read once.

    Cached, so it is usable as a FastAPI dependency and as a plain call. Tests that
    change the environment call ``get_settings.cache_clear()``.
    """
    return Settings()
