# Session Log - Shiva Kumar

## 2026-09-05
- **What was done**: Hash chain, explicit genesis entry, tamper index verification, local RFC 3161 hook, content-addressed S3 storage.
- **Agent used**: Claude Code
- **Decided**: Genesis prev_hash is explicit 64-char zeros; verify_chain returns ChainVerification with exact broken index.
- **Rejected**: External TSA calls (strictly forbidden for offline reproducibility); report generation and BSA §63(4) Part A output (deferred to VerdictRecord ticket).

## 2026-09-06
- **What was done**: Hardened hash chain verification against 5 independent tamper attacks (mutated payload, swapped entries, deleted middle entry, inserted entry, recomputed hash attack).
- **Failure reasons**: Structured `ChainVerification` returning exact broken link index and explicit failure reason string.
- **Offline check**: Verified chain integrity without network access by monkeypatching socket.socket.
- **Append-only API**: Verified zero update/edit/modify/patch functions exist in the evidence module.
- **Decided**: Recomputed hash attack tested with internally valid entry hashes to ensure linkage checks catch sophisticated tampering.
- **Rejected**: In-place edits (corrections must be append-only new records); verify-time RFC 3161 authority network calls.

## 2026-09-06 (Continued)
- **What was done**: Implemented `export.py` for officer compliance reports in PDF and DOCX from a unified `OfficerReportModel`.
- **Dependencies added**: `reportlab`, `python-docx` (pure wheels, no system binaries).
- **Enforced rules**: Human confirmation gate; strict verdict phrasing (PASS / REVIEW / POTENTIAL VIOLATION); zero occurrences of "violation confirmed" or "non-compliant"; explicit refusal and `INSUFFICIENT_EVIDENCE` handling; 100% clause reference citations.
- **Agent used**: Claude Code

## 2026-09-06 (Continued)
- **What was done**: Fixed vocabulary alignment on PR #41. Replaced internal string states with `Verdict` and `FieldState` enums from `app.contracts`. Expanded `test_forbidden_vocabulary` to block `non_compliant` and `noncompliant`.

## 2026-09-07 - PR #46 (EVD-005) Review Fixes & Rebase
- **Rebase**: Rebased `evd-005-retention-purge` onto `origin/main`.
- **Enum Alignment**: Adopted `EvidenceAssetType` (`PRODUCT_IMAGE`, `AUDIT_LOG`, `PERSONAL_DATA`) from `app.contracts`. Deleted local enum definition in `domain.py`.
- **Hash Integrity**: Integrated `asset_type` as the fifth field in `compute_entry_hash`.
- **Zero Defaults**: Removed default arguments from `create_genesis_entry` and `append_entry`, making `asset_type` mandatory across all call sites.
- **Storage & False Attestation**: Purge verifies CAS object existence before deleting; returns `(False, "asset_not_found")` and writes zero audit records to the chain if missing. Catches specific `ClientError` 404/NoSuchKey.
- **Legal Hold**: Enforced hold on unreviewed `POTENTIAL_VIOLATION` records and `CONFIRM`/`OVERRIDE`; release gated strictly on `REJECT`.
- **Quality Gates**: All local checks (`ruff format --check .`, `ruff check .`, `lint-imports`, `pytest`) passing green.
- **Agent**: Claude Code.

## 2026-09-07 - EVD-006 Report Export Migration
- **What was done**: Migrated report export from mock structures to real Pydantic `VerdictRecord` and SQLAlchemy `ReviewRow` contracts.
- **Human confirmation gate**: Enforced using finalising actions (`ReviewAction.CONFIRM`, `REJECT`, `OVERRIDE`) from `ReviewRow`.
- **Test updates**: Updated fixtures in `tests/modules/evidence/test_report_export.py` with real contract instances and corrected enum members (`VERIFIED`, `RETAIL_SALE_PRICE`, `MANDATORY`, `PADDLEOCR`).
- **Defect Falsifications**:
  - Defect A (Confirmation Gate): Disabled gate check in `export.py`; verified `test_human_confirmation_gate` failed RED, restored.
  - Defect B (Refusal Rendering): Replaced 'Measurement declined' in `docx_renderer.py`; verified `test_measurement_refusal_rendering` failed RED, restored.
- **Verification**: All 8 report export tests passing green; evidence suite passing 45/45 runnable tests.
- **Agent**: Claude Code.

## CMP-001 Part A: Manufacturer Complaint Loop Domain Implementation

- **Status**: Completed Part A (Domain State Machine & Structural Confirmation Gate).
- **Module**: `app/modules/complaints/` (`domain.py`, `service.py`).
- **Design & Invariants**:
  - `ComplaintStatus` enum: `RAISED`, `ACKNOWLEDGED`, `RESOLVED`, `REJECTED`.
  - Append-only transitions: Returning a new `ComplaintRecord` rather than mutating history in-place.
  - Re-opening a resolved/rejected complaint generates a new `RAISED` record with `supersedes_id` pointing to the prior complaint.
  - Structural human-confirmation gate: Factory `create_complaint_from_verdict` strictly enforces `review_row.action` in `{ReviewAction.CONFIRM, ReviewAction.OVERRIDE}`; raises `UnconfirmedVerdictComplaintError` otherwise.
  - Forbidden vocabulary guarded: Verified omission of forbidden terms (`violation confirmed`, `illegal`, `non-compliant`, etc.).
- **Falsification Verification**:
  - Injected defect bypassing `target_status` check in `ComplaintRecord.transition_to`.
  - Ran `uv run pytest tests/modules/complaints/test_complaints_domain.py` without `-x`:
    ```text
    FAILED tests/modules/complaints/test_complaints_domain.py::test_illegal_transitions - Failed: DID NOT RAISE IllegalComplaintTransitionError
    ======================= 1 failed, 4 passed in 8.72s =======================
    ```
  - Reverted `domain.py`: Suite returned clean green (5 passed in 5.03s).
