# TICKETS.md — board state, 2026-09-06 (end of session)

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
| CI-002 frontend build gate | Abhiram | done — *no ClickUp ticket* | #30 |
| COR-001 | Abhiram | done | #6 |
| INF-001 CODEOWNERS + import guard | Abhiram | done | #7 |
| INF-002 handoff | Abhiram | done | #10 |
| INF-003 gh auth login steps | Abhiram | done | #11 |
| CTR-002 contracts v1 | Abhiram | done | #17 |
| CTR-003 deep-copy rule parameters into the snapshot | Abhiram | done — *no ClickUp ticket* | #33 |
| CORE-001 auth, RBAC, jurisdiction scoping | Abhiram | done | #25 |
| PIP-001 verdict assembly + rule parameter snapshot | Abhiram | done | #28 |
| EXT-001 | Sitanshu | done | #4 |
| EXT-002 country of origin | Sitanshu | done | #18 |
| EXT-003 name, dimensions, unit price | Sitanshu | done | #24 |
| EXT-004 | Sitanshu | to do — not started | — |
| RUL-001 | Jashwanth | done | #21 |
| RUL-002 Rule 8, Rule 9, sector overrides, medical devices, Combination/Group | Abhiram | done | #32 |
| RUL-003 multi-piece package 2(kc) + food proviso | Abhiram | done — *no ClickUp ticket* | #36 |
| VIS-001 | Akshaya | done | #5 |
| VIS-002 PDP detection + OCR | Akshaya | done | #20 |
| VIS-003 | Akshaya | in progress — rework | — |
| TAM-001 | Akshaya | to do — queued behind VIS-003 | — |
| MEA-001 | Yashashvi | done | #9 |
| MEA-002 artwork mode + Rule 9 contrast | Yashashvi | done | #13 |
| MEA-003 ratio + margins | Yashashvi | done | #22 |
| EVD-001 | Shiva Kumar | done | #12 |
| EVD-002 MinIO + BSA report | Shiva Kumar | done | #23 |
| EVD-003 hash chain verification + append-only | Shiva Kumar | done | #31 |
| FNT-001 | Yashwanth (reassigned from Vineeth) | done | #14 |
| FNT-002 officer design system, verdict detail, review queue | Abhiram | done | #35 |
| DAT-001 corpus | Aashritha | in progress — rework | #8 merged (tooling), #16 open |

**Built without a ClickUp ticket:** CI-002, CTR-003, RUL-003. Create them retrospectively
so the board matches the repository — three merged PRs with no ticket behind them is the
board lying, not a paperwork detail.

**RUL-002 and RUL-003 were reassigned.** Both were on Jashwanth in the previous board
state; both were built by Abhiram. `bck/app/modules/rules/` ownership in `AGENTS.md` still
reads Jashwanth while the module README reads @Abhiram-0910. Reconcile the two files
together — they currently disagree.

**Unassigned, never started:** `fnt-admin` (Rohan). Reserve: Likitha.

**Free for a new ticket:** Sitanshu (after EXT-004), Yashashvi, Shiva Kumar. Vineeth
remains unavailable.

---

## Owed on every future ticket

Each new ticket carries a personalised **"Before you raise the PR"** verification block
at the bottom, built from that ticket's own acceptance criteria and its specific failure
modes. `Files` fields must include the matching test path.

**`session-log/<name>.md` must appear in every future ticket's `Files` field.** Its
absence has been producing false out-of-scope flags on every review this session: the
session protocol in `CLAUDE.md` requires the log to be updated, the ticket's Files field
does not permit it, and the reviewer then flags a required edit as scope creep. Add it to
the template rather than arguing it per ticket.
