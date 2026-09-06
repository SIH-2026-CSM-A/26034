"""Every test in this package runs twice, once per designation profile.

That is the point of the fixture below. The acceptance criterion is not "the config value
changed" — it is that *behaviour is identical whichever nomenclature a deployment uses*.
The only way to show that is to run the same permission and scoping assertions against
both, so ``designation_profile`` is ``autouse`` and parameterised, and every test in
``tests/core/`` is collected once per profile.

``alternate`` is a second, deliberately different naming. It is invented for this test
and is not a claim about any particular state's titles — it exists so that no word in it
appears in the default, so a check anywhere comparing against the literal "Controller",
"Deputy" or "Inspector" fails one of the two runs.
"""

import json
from collections.abc import Iterator

import pytest
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.config import DEFAULT_ROLE_DESIGNATIONS, Settings, get_settings
from app.core.rbac import Jurisdiction, Principal, RoleTier, scope_to_jurisdiction

JWT_SECRET = "test-signing-key-not-used-anywhere-real"

DESIGNATION_PROFILES: dict[str, dict[RoleTier, str]] = {
    "default": DEFAULT_ROLE_DESIGNATIONS,
    "alternate": {
        RoleTier.STATE: "Commissioner, Weights and Measures",
        RoleTier.REGIONAL: "Joint Director, Weights and Measures",
        RoleTier.DISTRICT: "Field Officer, Weights and Measures",
    },
}


@pytest.fixture(params=sorted(DESIGNATION_PROFILES), autouse=True)
def designation_profile(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    """Configure the process with one naming profile and hand back its name."""
    designations = DESIGNATION_PROFILES[request.param]
    # A developer's own .env must not decide what these tests see.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv(
        "ROLE_DESIGNATIONS",
        json.dumps({tier.value: name for tier, name in designations.items()}),
    )
    monkeypatch.delenv("OFFICERS", raising=False)
    monkeypatch.delenv("COST_CEILINGS", raising=False)
    get_settings.cache_clear()
    yield request.param
    get_settings.cache_clear()


class Base(DeclarativeBase):
    """Declarative base for this test's throwaway schema."""


class ScanRecord(Base):
    """A stand-in for any record an officer might list: it lives in a jurisdiction.

    Deliberately not a contracts type. What is under test is that a SELECT against a
    mapped table comes back narrowed, and any table with these three columns exercises
    that identically.
    """

    __tablename__ = "scan_record"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String)
    district: Mapped[str] = mapped_column(String)


class UnscopedRecord(Base):
    """A table with no jurisdiction columns at all."""

    __tablename__ = "unscoped_record"

    id: Mapped[str] = mapped_column(String, primary_key=True)


# Two states, two regions in the state under test, three districts in the region under
# test. Every principal below has records outside its authority to fail to see.
RECORDS = (
    ("mh-pune-pune", "Maharashtra", "Pune", "Pune"),
    ("mh-pune-satara", "Maharashtra", "Pune", "Satara"),
    ("mh-pune-solapur", "Maharashtra", "Pune", "Solapur"),
    ("mh-nagpur-nagpur", "Maharashtra", "Nagpur", "Nagpur"),
    ("mh-nagpur-wardha", "Maharashtra", "Nagpur", "Wardha"),
    ("ka-bengaluru-bengaluru", "Karnataka", "Bengaluru", "Bengaluru Urban"),
    ("ka-mysuru-mysuru", "Karnataka", "Mysuru", "Mysuru"),
)

INSPECTOR = Principal(
    subject="inspector",
    tier=RoleTier.DISTRICT,
    jurisdiction=Jurisdiction(state="Maharashtra", region="Pune", district="Satara"),
)
DEPUTY = Principal(
    subject="deputy",
    tier=RoleTier.REGIONAL,
    jurisdiction=Jurisdiction(state="Maharashtra", region="Pune"),
)
CONTROLLER = Principal(
    subject="controller",
    tier=RoleTier.STATE,
    jurisdiction=Jurisdiction(state="Maharashtra"),
)


@pytest.fixture
def session() -> Iterator[Session]:
    """A populated in-memory database. SQLite ships with Python; nothing to install."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            ScanRecord(id=id_, state=state, region=region, district=district)
            for id_, state, region, district in RECORDS
        )
        session.commit()
        yield session
    engine.dispose()


def visible_ids(session: Session, principal: Principal) -> set[str]:
    """Run the scoped SELECT the way an endpoint would and collect what came back."""
    statement = scope_to_jurisdiction(select(ScanRecord), principal, ScanRecord)
    return {record.id for record in session.scalars(statement)}
