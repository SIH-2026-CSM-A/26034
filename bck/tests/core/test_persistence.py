"""What the scan-path tables promise, proved against a real database.

The substrate here is a **sync** ``Session`` on in-memory SQLite. Production runs
``AsyncSession`` on PostgreSQL, so :func:`app.core.db.get_session`, the async engine and
the real ``jsonb`` and native enum types are covered in ``tests/persistence/`` instead.
That split is deliberate: an async SQLite driver is a dependency nothing ships with, and
what this file proves — which column holds what, what the database may and may not
supply, and that a scoped SELECT narrows — is not dialect-specific.

Every test here runs once per designation profile (see ``conftest.py``).
"""

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.contracts import (
    DeclarationField,
    EvidenceAssetType,
    FieldState,
    RuleDefinition,
    RuleParameterSnapshot,
    RuleSeverity,
    RuleStatus,
    ToleranceBasis,
    Verdict,
)
from app.core.models import (
    Base,
    CalibrationMethod,
    EvidenceEntryRow,
    FieldFindingRow,
    Scan,
    ScanSourceType,
    ScanStatus,
    VerdictRow,
)
from app.core.rbac import Principal, scope_to_jurisdiction
from app.modules.evidence.chain import append_entry, create_genesis_entry, verify_chain
from tests.core.conftest import CONTROLLER, DEPUTY, INSPECTOR, RECORDS

RULE_SET_VERSION = "2026.09.1"
EXISTING_GAZETTE = "GSR-629E__2017-06-23__amendment-rules-2017.pdf"

SCAN_IDS = {label: UUID(int=index) for index, (label, *_) in enumerate(RECORDS, start=1)}
"""One stable id per jurisdiction fixture, so a result set can be named in assertions."""

LABELS = {scan_id: label for label, scan_id in SCAN_IDS.items()}


@pytest.fixture
def db() -> Iterator[Session]:
    """An empty database carrying the schema under test."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def a_scan(
    label: str = "subject",
    state: str = "Maharashtra",
    region: str | None = "Pune",
    district: str | None = "Satara",
) -> Scan:
    """One scan in a named jurisdiction. Everything not under test takes a fixed value."""
    return Scan(
        id=SCAN_IDS.get(label, UUID(int=999)),
        source_type=ScanSourceType.PHYSICAL_LABEL,
        status=ScanStatus.COMPLETE,
        calibration_method=CalibrationMethod.NONE,
        state=state,
        region=region,
        district=district,
        officer_id="inspector",
        rule_set_version=RULE_SET_VERSION,
        image_refs=[{"role": "front", "object_key": "scans/front.jpg"}],
        capture_metadata={"device": "test-harness"},
    )


def a_rule(rule_id: str = "TEST-RULE") -> RuleDefinition:
    """A minimal valid contracts rule. Synthetic: it encodes no provision.

    The gazette reference is a real file in ``rules-corpus/`` because
    :class:`~app.contracts.RuleDefinition` refuses to construct without one, but the
    source text says outright that it states nothing, so this fixture makes no legal
    claim. Nested containers in ``parameters`` are the point of it — the snapshot test
    below mutates them.
    """
    return RuleDefinition(
        rule_id=rule_id,
        clause_ref="Test clause",
        gazette_ref=EXISTING_GAZETTE,
        source_text="Synthetic source text used only by a persistence test.",
        status=RuleStatus.VERIFIED,
        effective_from=date(2020, 1, 1),
        severity=RuleSeverity.MANDATORY,
        parameters={"bands": [{"upper": 50, "height_mm": 1}], "units": ["g", "kg"]},
        tolerance=Decimal("0.05"),
        tolerance_basis=ToleranceBasis.PERCENTAGE,
    )


def a_verdict(db: Session, scan: Scan) -> VerdictRow:
    """Persist ``scan`` and a verdict against it, so findings have somewhere to hang."""
    verdict = VerdictRow(
        scan_id=scan.id,
        verdict=Verdict.REVIEW,
        subject_ref=str(scan.id),
        rule_set_version=RULE_SET_VERSION,
        evaluated_at=datetime(2026, 9, 6, 9, 0, tzinfo=UTC),
        field_providers={DeclarationField.NET_QUANTITY.value: "PADDLEOCR"},
    )
    db.add_all([scan, verdict])
    db.commit()
    return verdict


def a_finding(
    verdict: VerdictRow, state: FieldState, rule_id: str = "TEST-RULE"
) -> FieldFindingRow:
    """One finding in ``state``, with a snapshot of :func:`a_rule` behind it.

    ``rule_id`` is taken from the snapshot rather than passed separately, because that is
    the only place it may come from: the column is a queryable copy of one field of the
    document beside it, and the two agreeing is the whole basis for querying it.
    """
    snapshot = RuleParameterSnapshot.from_rule(a_rule(rule_id), RULE_SET_VERSION).model_dump(
        mode="json"
    )
    return FieldFindingRow(
        verdict_id=verdict.id,
        field=DeclarationField.NET_QUANTITY,
        rule_id=snapshot["rule_id"],
        state=state,
        reason=f"fixture finding recorded as {state.value}",
        rule_snapshot=snapshot,
        evidence_span_ids=["span-1"],
        evidence_regions=[{"polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]}],
    )


# --- Jurisdiction scoping, on the real Scan table ---------------------------------


@pytest.fixture
def scans(db: Session) -> Session:
    """The seven fixture jurisdictions, as rows in ``scans``."""
    db.add_all(a_scan(label, state, region, district) for label, state, region, district in RECORDS)
    db.commit()
    return db


def visible_labels(db: Session, principal: Principal) -> set[str]:
    """Run the scoped SELECT the way an endpoint would and name what came back."""
    return {
        LABELS[scan.id] for scan in db.scalars(scope_to_jurisdiction(select(Scan), principal, Scan))
    }


def test_a_district_officer_reads_their_own_district_and_no_other(scans: Session) -> None:
    assert visible_labels(scans, INSPECTOR) == {"mh-pune-satara"}


def test_an_out_of_jurisdiction_scan_is_absent_from_a_district_officers_query(
    scans: Session,
) -> None:
    """The acceptance criterion, stated as absence rather than as a count.

    A neighbouring district, a district in another region of the same state, and another
    state entirely: none of them is in what the inspector can read.
    """
    visible = visible_labels(scans, INSPECTOR)
    for absent in (
        "mh-pune-pune",
        "mh-pune-solapur",
        "mh-nagpur-nagpur",
        "mh-nagpur-wardha",
        "ka-bengaluru-bengaluru",
        "ka-mysuru-mysuru",
    ):
        assert absent not in visible


def test_a_state_officer_reads_every_scan_in_their_state(scans: Session) -> None:
    visible = visible_labels(scans, CONTROLLER)
    assert visible == {
        "mh-pune-pune",
        "mh-pune-satara",
        "mh-pune-solapur",
        "mh-nagpur-nagpur",
        "mh-nagpur-wardha",
    }
    assert not {"ka-bengaluru-bengaluru", "ka-mysuru-mysuru"} & visible


def test_a_regional_officer_sits_between_the_two(scans: Session) -> None:
    assert visible_labels(scans, DEPUTY) == {
        "mh-pune-pune",
        "mh-pune-satara",
        "mh-pune-solapur",
    }


def test_every_scan_is_reachable_by_someone(scans: Session) -> None:
    """Guards the guard: a WHERE clause matching nothing would pass every test above."""
    assert len(scans.scalars(select(Scan)).all()) == len(RECORDS)


# --- INSUFFICIENT_EVIDENCE survives storage as itself -----------------------------


def test_every_field_state_survives_a_round_trip_as_itself(db: Session) -> None:
    """Each of the five states is written, read back in a new query, and still itself."""
    verdict = a_verdict(db, a_scan())
    # One declaration against five different rules — which is what (verdict_id, field)
    # being non-unique is for, and what (verdict_id, field, rule_id) still forbids twice.
    db.add_all(a_finding(verdict, state, f"TEST-RULE-{state.value}") for state in FieldState)
    db.commit()
    db.expunge_all()

    stored = {finding.reason: finding.state for finding in db.scalars(select(FieldFindingRow))}
    assert stored == {f"fixture finding recorded as {state.value}": state for state in FieldState}
    # StrEnum compares equal to its own value, so the mapping above would still hold if the
    # column were a bare String. This is what says the state came back as the enum.
    assert all(isinstance(state, FieldState) for state in stored.values())


def test_insufficient_evidence_does_not_come_back_as_fail(db: Session) -> None:
    """The constraint named on its own, because it is the one that matters.

    "We could not read it" and "it is not there" carry different legal consequences.
    A round trip that turned one into the other would be a wrongful flag written by
    storage rather than by evaluation.
    """
    verdict = a_verdict(db, a_scan())
    db.add(a_finding(verdict, FieldState.INSUFFICIENT_EVIDENCE))
    db.commit()
    db.expunge_all()

    reloaded = db.scalars(select(FieldFindingRow)).one()
    assert reloaded.state is FieldState.INSUFFICIENT_EVIDENCE
    assert reloaded.state is not FieldState.FAIL


def test_no_outcome_column_has_a_value_the_database_could_supply() -> None:
    """The hard constraint, as a property of the schema rather than of one insert.

    Neither column is nullable and neither has a default of any kind, so there is no
    value storage is entitled to invent for an outcome. A ``server_default`` added here
    for any reason turns this red.
    """
    for column in (FieldFindingRow.__table__.c.state, VerdictRow.__table__.c.verdict):
        assert column.nullable is False
        assert column.default is None
        assert column.server_default is None


# --- The rule snapshot is stored, not joined --------------------------------------


def test_a_stored_snapshot_does_not_move_when_the_rule_does(db: Session) -> None:
    """Amend the rule after the finding is written; the finding does not re-adjudicate.

    The mutation is on the source rule's own nested ``parameters`` containers, which is
    the shape a rule amendment takes. If persistence held a rule reference and rehydrated
    through it, the reloaded snapshot would follow the edit.
    """
    rule = a_rule()
    snapshot = RuleParameterSnapshot.from_rule(rule, RULE_SET_VERSION)

    verdict = a_verdict(db, a_scan())
    finding = a_finding(verdict, FieldState.FAIL)
    finding.rule_snapshot = snapshot.model_dump(mode="json")
    db.add(finding)
    db.commit()
    db.expunge_all()

    rule.parameters["bands"][0]["height_mm"] = 99
    rule.parameters["units"].append("tonne")

    reloaded = RuleParameterSnapshot.model_validate(
        db.scalars(select(FieldFindingRow)).one().rule_snapshot
    )
    assert reloaded == snapshot
    assert reloaded.parameters["bands"] == [{"upper": 50, "height_mm": 1}]
    assert reloaded.tolerance == Decimal("0.05")
    assert isinstance(reloaded.tolerance, Decimal)


def test_a_verdict_row_holds_no_reference_to_a_rules_table(db: Session) -> None:
    """There is nothing to join through, which is what makes the snapshot load-bearing."""
    assert VerdictRow.__table__.foreign_keys == {
        key for key in VerdictRow.__table__.foreign_keys if key.column.table.name == "scans"
    }
    assert not {"rule_id", "rule_set_id", "rule_definition_id"} & set(VerdictRow.__table__.c.keys())


# --- The evidence chain verifies after a round trip -------------------------------


def test_an_evidence_chain_verifies_after_a_round_trip(db: Session) -> None:
    """Genesis plus two appends, stored and reloaded, still verifies.

    The two type choices this holds down are ``timestamp`` as text and the payload as
    text. A ``timestamptz`` re-rendered on read, or a payload normalised by ``jsonb``,
    produces different bytes from the ones the chain hashed, and verification then
    reports a broken chain nobody touched.
    """
    scan = a_scan()
    db.add(scan)
    db.commit()

    genesis = create_genesis_entry(
        {"event": "scan_received"}, "2026-09-06T09:00:00+00:00", EvidenceAssetType.AUDIT_LOG
    )
    second = append_entry(
        genesis,
        {"event": "verdict_assembled"},
        "2026-09-06T09:01:00+00:00",
        EvidenceAssetType.AUDIT_LOG,
    )
    third = append_entry(
        second,
        {"event": "report_exported"},
        "2026-09-06T09:02:00+00:00",
        EvidenceAssetType.PRODUCT_IMAGE,
    )
    built = [genesis, second, third]
    assert verify_chain(built).is_valid

    db.add_all(
        EvidenceEntryRow(
            scan_id=scan.id,
            sequence=entry.sequence,
            timestamp=entry.timestamp,
            payload_hash=entry.payload_hash,
            prev_hash=entry.prev_hash,
            entry_hash=entry.entry_hash,
            payload_json=json.dumps(entry.payload, sort_keys=True, separators=(",", ":")),
            asset_type=entry.asset_type,
            storage_ref=None,
        )
        for entry in built
    )
    db.commit()
    db.expunge_all()

    rows = db.scalars(select(EvidenceEntryRow).order_by(EvidenceEntryRow.sequence)).all()
    reloaded = [
        type(genesis)(
            sequence=row.sequence,
            timestamp=row.timestamp,
            payload_hash=row.payload_hash,
            prev_hash=row.prev_hash,
            entry_hash=row.entry_hash,
            payload=row.payload_json,
            asset_type=row.asset_type,
        )
        for row in rows
    ]

    verification = verify_chain(reloaded)
    assert verification.is_valid, verification.reason
    assert [entry.entry_hash for entry in reloaded] == [entry.entry_hash for entry in built]


def test_relabelling_an_asset_type_breaks_the_entry_hash() -> None:
    """``asset_type`` is inside the entry hash, not merely stored beside it.

    It is the field a retention window is read from. Outside the hash, an entry could be
    relabelled from one asset class to another, become purgeable under a different rule,
    and :func:`verify_chain` would still report the chain intact — a tamper vector on the
    one structure whose entire purpose is detecting tampering.

    Nothing else in the suite would notice: every other assertion about an entry hash
    recomputes it from the same inputs, so a field left out of the hash is invisible.
    """
    payload = {"event": "scan_received"}
    timestamp = "2026-09-06T09:00:00+00:00"

    as_capture = create_genesis_entry(payload, timestamp, EvidenceAssetType.PRODUCT_IMAGE)
    as_audit_log = create_genesis_entry(payload, timestamp, EvidenceAssetType.AUDIT_LOG)

    assert as_capture.payload_hash == as_audit_log.payload_hash, (
        "the payloads are identical; only asset_type differs"
    )
    assert as_capture.entry_hash != as_audit_log.entry_hash

    relabelled = as_capture.model_copy(update={"asset_type": EvidenceAssetType.AUDIT_LOG})
    assert not verify_chain([relabelled]).is_valid
    assert verify_chain([relabelled]).reason == "entry_hash_mismatch"
