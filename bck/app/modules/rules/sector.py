"""Strategy dispatch from a confirmed product category to its controlling framework.

Every sector override in the store is a row in a table this module builds by reading the
store. There is no ``if category is MEDICAL_DEVICE`` anywhere, and adding a sector is a
rule in ``data/rules.yaml`` plus a member of
:class:`~app.modules.rules.base.ProductCategory` — no existing branch is edited, so no
existing sector can be broken by the addition.

A sector override is a **carve-out, not a stricter path.** G.S.R. 778(E) does not raise
the bar for medical devices; it moves height, width and the panel declaration to the
Medical Devices Rules, 2017 entirely, and removes the Rule 33 relaxation that would
otherwise be available. Evaluating a carved-out obligation against the packaged rules
anyway produces a finding under a rule that does not apply to the package.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from .base import OverrideTarget, ProductCategory
from .conditions import SectorOverrideCondition
from .loader import is_active, load_default_rules
from .results import SectorOverride


class SectorRoutedError(LookupError):
    """A packaged-rule threshold was requested for a sector that does not use it.

    Raised rather than returned so a sector-blind caller fails loudly. A lookup that
    quietly hands back a Rule 7 Table-I height for a medical device produces a
    millimetre requirement with no legal basis, and nothing downstream can tell that
    figure apart from one the gazette actually states.
    """


def sector_overrides(
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> Mapping[OverrideTarget, SectorOverride]:
    """Return the obligations routed away from the packaged rules for a category.

    Empty for ``None`` — an unconfirmed category routes nothing — and empty for a
    category no rule in the store speaks to. Only overrides effective on
    ``evaluation_date`` count: G.S.R. 778(E) came into force on publication, and a scan
    dated before that is adjudicated under the rules as they then stood.
    """
    if product_category is None:
        return {}

    routed: dict[OverrideTarget, SectorOverride] = {}
    for rule in load_default_rules():
        condition = rule.conditions
        if not isinstance(condition, SectorOverrideCondition):
            continue
        if condition.sector is not product_category or not is_active(rule, evaluation_date):
            continue
        for target in condition.overrides:
            routed[target] = SectorOverride(
                sector=condition.sector,
                target=target,
                controlling_framework=condition.controlling_framework,
                rule_id=rule.rule_id,
            )
    return routed


def controlling_framework(
    target: OverrideTarget,
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> SectorOverride | None:
    """Return the framework controlling one obligation, or ``None`` for the packaged rules."""
    return sector_overrides(product_category, evaluation_date).get(target)


def rule_33_relaxation_applies(
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> bool:
    """Return whether the Rule 33 power to relax remains available to a category.

    False where a sector rule disapplies it. G.S.R. 778(E) paragraph 4 inserts Rule
    33(2) so that a medical device cannot be granted the relaxation *and* be routed to
    the Medical Devices Rules, 2017 at the same time.
    """
    if product_category is None:
        return True

    for rule in load_default_rules():
        condition = rule.conditions
        if not isinstance(condition, SectorOverrideCondition):
            continue
        if (
            condition.sector is product_category
            and condition.disapplies_rule_33_relaxation
            and is_active(rule, evaluation_date)
        ):
            return False
    return True


def pdp_declaration_mandatory(
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> bool:
    """Return whether the packaged rules still mandate the panel declaration.

    False once Rule 2(h) is routed elsewhere. The declaration does not disappear — the
    Medical Devices Rules, 2017 govern it — so a caller reads this as "not ours to
    check", never as "not required".
    """
    return (
        controlling_framework(OverrideTarget.PDP_DECLARATION, product_category, evaluation_date)
        is None
    )
