
### 2026-09-08 — VerdictDetail Geometry Cleanup — *Antigravity*

**Done**
- Checked `ScanDetail` and `FieldFinding` response schemas for polygon or bounding-box fields, confirming none exist.
- Removed the hardcoded UI overlay and the associated test fixtures since drawing fabricated coordinates violates compliance constraints. 
- Modified `fnt/src/officer/VerdictDetail.tsx` and `fnt/src/officer/components/CapturePlate.tsx` to omit the overlay rendering.

**Decided**
- Rendered an empty `CapturePlate` component because real geometry is unavailable and fabricated data cannot be shown to officers.
