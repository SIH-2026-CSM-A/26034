"""Refuse the test shape that has silently passed five times.

**The failure.** With no confirmed product category, every rule in
:data:`~app.pipeline.dispositions.SECTOR_GOVERNED_RULES` is settled by the sector gate —
INSUFFICIENT_EVIDENCE, before its own builder runs. A test that then asserts something
about that rule's downstream handling is asserting about the gate: it passes whether the
handling exists, is broken, or was deleted. Three tests here passed against injected
defects for exactly that reason, and two more were written wrong on the same
misunderstanding.

**Why a note was not enough.** It is documented in ``pipeline/README.md`` and in the
module docstring of ``test_orchestrator.py``, and it still recurred. Prose does not run.

**What this does.** :func:`findings_for_rule` is the only sanctioned way to pick a rule's
findings out of a result, and it fails loudly when everything it selected came from the
gate. It needs no product-category argument, which is the point — an argument is a thing a
test can pass wrongly. It reads the condition off the findings themselves: if every
selected finding carries :data:`~app.pipeline.rule_findings.UNCONFIRMED_CATEGORY_REASON`,
then whatever the test meant to exercise did not run, whatever it believes it configured.

``test_sector_gate_guard.py`` keeps this the only route, by refusing a direct
``rule_id == "..."`` comparison anywhere else in this package.
"""

from collections.abc import Sequence

from app.contracts import FieldFinding, FieldState
from app.pipeline.dispositions import SECTOR_GOVERNED_RULES
from app.pipeline.rule_findings import UNCONFIRMED_CATEGORY_REASON

UNGATED_BY = {
    "R7-2-TABLE-I": "food or cosmetics",
    "R7-3-WIDTH-RATIO": "food or cosmetics",
    "R8-1-PDP-PLACEMENT": "food or cosmetics",
    "R6-1-A": "medical_device or cosmetics",
    "R6-1-D": "medical_device or food",
    "R6-1-D-GSR-722E": "medical_device or food",
}
"""A category that leaves each gated rule with the packaged rules, for the error message.

Read off the store's own sector overrides: G.S.R. 778(E) routes height, width and the panel
declaration for medical devices, Explanation III routes the manufacturer declaration for
food, and the cosmetics rule routes the date declaration. Confirming a category that carves
*this* rule out is no better than confirming none — it settles the rule just as early — so
the suggestion has to name a category that leaves it alone.
"""


def findings_for_rule(
    findings: Sequence[FieldFinding],
    rule_id: str,
    *,
    gate_is_the_subject: bool = False,
) -> list[FieldFinding]:
    """Every finding for one rule, refusing a selection the sector gate already decided.

    Pass ``gate_is_the_subject=True`` when the gate is what the test is about — that is a
    legitimate and necessary thing to assert, and it should be stated rather than inferred.
    """
    selected = [finding for finding in findings if finding.rule_snapshot.rule_id == rule_id]
    if gate_is_the_subject or not selected:
        return selected

    gate_settled = [
        finding
        for finding in selected
        if finding.state is FieldState.INSUFFICIENT_EVIDENCE
        and finding.reason == UNCONFIRMED_CATEGORY_REASON
    ]
    if len(gate_settled) == len(selected):
        raise AssertionError(_explain(rule_id))
    return selected


def _explain(rule_id: str) -> str:
    """Say what went wrong, and the two ways out, in the terms of this rule."""
    suggestion = UNGATED_BY.get(rule_id)
    ungated = (
        f"Confirm {suggestion}, which leaves {rule_id} with the packaged rules"
        if suggestion
        else "Confirm a product category that does not carve this rule out"
    )
    gated = rule_id in SECTOR_GOVERNED_RULES
    return (
        f"every finding selected for {rule_id} was settled by the sector gate, not by the "
        f"builder this test is exercising.\n\n"
        f"{rule_id} is {'sector-gated' if gated else 'settled'}: with no confirmed product "
        f"category the gate answers INSUFFICIENT_EVIDENCE before the rule's own builder "
        f"runs, so this assertion holds whether that builder works, is broken, or is "
        f"deleted. Three tests in this package passed against injected defects this way.\n\n"
        f"Two ways out:\n"
        f"  - {ungated}.\n"
        f"  - Assert against a rule the gate does not touch (R8-1-FREE-SPACE is a "
        f"measurement rule and is ungated; R6-1-C and R6-1-E are declaration rules).\n\n"
        f"If the gate itself is the subject, say so: "
        f"findings_for_rule(..., gate_is_the_subject=True)."
    )
