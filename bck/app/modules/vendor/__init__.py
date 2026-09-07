"""Vendor self-scan module under VND-001.

Provides domain models, routing service, and persistence repository for
vendor-submitted scans.
"""

from app.modules.vendor.domain import VendorSubmission, VendorType
from app.modules.vendor.repository import (
    get_vendor,
    get_vendor_jurisdiction,
    get_vendor_scan,
    lookup_vendor_jurisdiction,
    persist_vendor_scan,
    persist_vendor_submission,
    record_vendor_scan,
    record_vendor_submission,
)
from app.modules.vendor.service import (
    RoutingDecision,
    RoutingResult,
    VendorRoutingResult,
    route_vendor_result,
    route_vendor_submission,
    route_verdict,
    scope_vendor_query,
)

__all__ = [
    "RoutingDecision",
    "RoutingResult",
    "VendorRoutingResult",
    "VendorSubmission",
    "VendorType",
    "get_vendor",
    "get_vendor_jurisdiction",
    "get_vendor_scan",
    "lookup_vendor_jurisdiction",
    "persist_vendor_scan",
    "persist_vendor_submission",
    "record_vendor_scan",
    "record_vendor_submission",
    "route_vendor_result",
    "route_vendor_submission",
    "route_verdict",
    "scope_vendor_query",
]
