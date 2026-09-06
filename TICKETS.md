# TICKETS.md — board state, 2026-09-06

ClickUp list `26034 Build` (`1300450000005736`), space `SIH Team` (`1300450000003833`).
Fields: `Module 26034` (dropdown), `Files` (text), `Branch` (text).
Statuses: `to do` · `doubt` · `in progress` · `review` · `done` · `complete`.

ClickUp rate limit has reset — use the connector directly to create and update
tickets from here on. **If it rate-limits again, stop and tell Abhiram to action the
change manually** — give him each ticket as title/assignee/status/priority/three
custom fields/description as one pasteable markdown block.

---

## Status summary

| Ticket | Owner | Status | PR |
|---|---|---|---|
| CI-001 | Abhiram | done | #3 |
| COR-001 | Abhiram | done | #6 |
| INF-001 CODEOWNERS + import guard | Abhiram | done | #7 |
| INF-002 handoff | Abhiram | done | #10 |
| INF-003 gh auth login steps | Abhiram | done | #11 |
| CTR-002 contracts v1 | Abhiram | done | #17 |
| CORE-001 auth, RBAC, jurisdiction scoping | Abhiram | done | #25 |
| EXT-001 | Sitanshu | done | #4 |
| EXT-002 country of origin | Sitanshu | done | #18 |
| EXT-003 name, dimensions, unit price | Sitanshu | done | #24 |
| RUL-001 | Jashwanth | done | #21 |
| RUL-002 sector overrides, Combination/Group packages | Jashwanth | **in progress, no PR yet** | — |
| VIS-001 | Akshaya | done | #5 |
| VIS-002 PDP detection + OCR | Akshaya | done | #20 |
| MEA-001 | Yashashvi | done | #9 |
| MEA-002 artwork mode + Rule 9 contrast | Yashashvi | done | #13 |
| MEA-003 ratio + margins | Yashashvi | done | #22 |
| EVD-001 | Shiva Kumar | done | #12 |
| EVD-002 MinIO + BSA report | Shiva Kumar | done | #23 |
| FNT-001 | Yashwanth (reassigned from Vineeth) | done | #14 |
| DAT-001 corpus | Aashritha | **in progress — root cause now correctly diagnosed by her own AI: fabricated annotations + empty-file placeholders. Plan confirmed correct: rewrite 4 real annotations from actual photo content, zip+send images to Abhiram outside git, close honestly at 4 real samples. Awaiting her manual annotation-rewrite step, then a fresh PR.** | #8 merged (tooling), #16 open |

**Unassigned, never started:** `tamper` module (originally Shivasai — no ticket ever
created). `fnt-admin` (Rohan). Reserve: Likitha.

**Everyone else is free for a new ticket:** Sitanshu, Akshaya, Yashashvi, Shiva Kumar.
Vineeth remains unavailable.

---

## Owed on every future ticket

Each new ticket carries a personalised **"Before you raise the PR"** verification block
at the bottom, built from that ticket's own acceptance criteria and its specific failure
modes. `Files` fields must include the matching test path.
