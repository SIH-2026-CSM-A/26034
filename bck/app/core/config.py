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

    Required to serve a scan. ``None`` by default and validated at application startup
    rather than defaulted to a path that might happen to exist: weights are gitignored and
    pre-cached, so the failure this guards is a fresh clone, and the honest place to find
    out is boot rather than the first request an officer makes.
    """

    ocr_det_model_dir: Path | None = None
    """PaddleOCR text-detection model directory. Explicit and local, so nothing downloads
    a model mid-scan — the demo has to survive the venue network failing."""

    ocr_rec_model_dir: Path | None = None
    """PaddleOCR text-recognition model directory. Same reasoning as the detector."""

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

    officers: tuple[OfficerCredential, ...] = ()
    """Officers who may log in. Empty by default: a deployment that configures none has
    no accounts, rather than a default account somebody forgets to remove."""

    @field_validator(
        "datasets_dir",
        "rules_corpus_dir",
        "pdp_weights_path",
        "ocr_det_model_dir",
        "ocr_rec_model_dir",
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
        for name in ("pdp_weights_path", "ocr_det_model_dir", "ocr_rec_model_dir"):
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
