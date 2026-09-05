# TICKETS.md — board state, 2026-09-05

ClickUp list `26034 Build` (`1300450000005736`), space `SIH Team` (`1300450000003833`).
Fields: `Module 26034` (dropdown), `Files` (text), `Branch` (text).
Statuses: `to do` · `doubt` · `in progress` · `review` · `done` · `complete`.

This file exists because the ClickUp connector is rate-limited. It is a mirror, not the
source of truth — the board is. Re-sync when the connector recovers.

---

## Status summary

| Ticket | Owner | Status | PR |
|---|---|---|---|
| CI-001 | Abhiram | done | #3 merged |
| COR-001 | Abhiram | done | #6 merged |
| INF-001 CODEOWNERS + import guard | Abhiram | done | #7 merged |
| INF-002 handoff | Abhiram | done | #10 merged |
| INF-003 gh auth login steps | Abhiram | done | merged |
| CTR-002 contracts v1 | Abhiram | in progress | — |
| EXT-001 | Sitanshu | done | #4 merged |
| EXT-002 country-of-origin | Sitanshu | to do | — |
| RUL-001 | Jashwanth | in progress | — |
| RUL-002 sector overrides | Jashwanth | to do | — |
| VIS-001 | Akshaya | done | #5 merged |
| VIS-002 PDP detection + OCR | Akshaya | in progress | — |
| MEA-001 | Yashashvi | done | #9 merged |
| MEA-002 artwork mode + Rule 9 contrast | Yashashvi | review, changes requested | #13 |
| EVD-001 | Shiva Kumar | done | #12 merged |
| EVD-002 MinIO wiring + BSA report | Shiva Kumar | to do | — |
| FNT-001 | Yashwanth (reassigned from Vineeth) | review | #14 |
| DAT-001 | Aashritha | in progress (corpus collection) | #8 merged (tooling only) |

Unassigned: `tamper` (Shivasai), `fnt-admin` (Rohan), reserve (Likhitha).

---

## Owed on every future ticket

Each new ticket carries a personalised **"Before you raise the PR"** verification block
at the bottom, built from that ticket's own acceptance criteria and its specific failure
modes.

`Files` fields must include the matching test path.
