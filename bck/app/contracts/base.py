"""Model configuration shared by every contract type.

Two settings, applied everywhere, for two reasons:

``extra="forbid"``
    A contract crossing six module boundaries must reject a field it does not know
    about. Silently accepting ``value=2.5`` on a measurement refusal, or a misspelt
    ``gazzette_ref``, would let a malformed record reach an evidence export looking
    well-formed.

``frozen=True``
    A verdict record and the rule parameters snapshotted into it are evidence. Once
    built they are read, hashed and exported, never edited in place.
"""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Base for every model in ``app.contracts``. Strict on input, immutable after."""

    model_config = ConfigDict(extra="forbid", frozen=True)
