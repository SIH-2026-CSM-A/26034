# HANDOFF-PROTOCOL.md

**Permanent. Read at the start of every chat on this project, alongside HANDOFF.md.**

When Abhiram says any of *"write the handoff"*, *"hand off to a new chat"*, *"transfer this
chat"*, or *"we're done here"* — execute this file end to end without being told the steps.
He should never have to explain the procedure again. If he does, this file failed.

Invoke the `context-compression` skill before writing anything.

---

## What "the handoff" means

Four things, in this order, in a single reply:

1. **Seven regenerated files**, written to `/mnt/user-data/outputs/` and presented with
   `present_files` so he can download them.
2. **A delete list** for project knowledge.
3. **An upload list** for project knowledge.
4. **The prompts for the new chat**, complete and pasteable, plus the verification questions.

Nothing is described in prose that could be given as a command. Nothing is left for him to
work out.

---

## 1 · The seven files

Always these seven, always regenerated in full — never "here's what changed", because he
replaces the whole file in project knowledge.

| File | What it carries |
|---|---|
| `HANDOFF.md` | Everything written down nowhere else. The big one. See structure below. |
| `TICKETS.md` | Board state: every ticket, owner, status, PR. Exact remaining items on open reworks. |
| `TODO.md` | Now / Next / Later / Bugs / Blocked / Done with dates / Cut / Deferred-and-what-it-costs. |
| `ARCHITECTURE.md` | Stack with rejections, structure, data flow, decisions, technical debt. |
| `AGENTS.md` | Cross-tool rules every agent reads. Ownership table, import rule, standing constraints. |
| `CLAUDE.md` | Claude Code specifics for this repo. Gotchas, constraints, files not to touch. |
| `RULES-CORPUS-INDEX.md` | Corpus files, known gaps, Rule 7 Table-I, Rule 6(11), encoded rule ids. |

### HANDOFF.md structure — keep these headings

- How Abhiram works with you
- What you can and cannot do (connector limits)
- The PR review protocol
- The recurring failure patterns
- Infrastructure state, dated
- Owners and usernames, with ownership shifts recorded
- Legal findings — expensive to rediscover
- Hard nos — do not re-propose
- Constraints discovered the hard way
- Decisions this session — do not re-litigate
- The frontend design system
- Where the board stands, dated
- Golden examples

### The test every line must pass

> *If this line disappeared, would the next session write, judge, refuse, structure or decide
> differently?*

Keep if yes. Cut if no. **True is not the bar.** Cut generic values, flattering description,
biography that doesn't change output, and anything included only because it happened.

**The rejected options matter as much as the chosen ones.** Without them a fresh session
re-proposes what was already killed. Every "we decided X" needs its "and rejected Y because".

Include, always, even if it feels like admitting fault: **claims that turned out to be wrong,
and who caught them.** A handoff that only records successes teaches the next session to be
confident in the same places this one was wrong.

---

## 2 · The delete list

Duplicate filenames break retrieval — a stale copy wins roughly half the time. Always give
three groups:

- **Replace:** the seven files above. Delete the old, upload the new.
- **Merged PR diffs and metas:** every `pr<n>*.md` and `pr-<n>-meta.json` whose PR has merged
  or closed. Name each file explicitly; do not write "the old PR files".
- **Superseded documents:** anything whose content has been absorbed into HANDOFF.md, or that
  describes a state no longer true (a rate-limited connector, an old prompt set).

Then state explicitly what to **keep**: open-PR diffs still in rework, and the permanent
product/team/environment set. Listing the keeps prevents him deleting something load-bearing.

---

## 3 · The upload list

The seven files, plus any still-open PR diff. Name them.

---

## 4 · The prompts for the new chat

Give all four, complete, in pasteable code blocks. Never a pointer to another document.

**Before prompt 1:** state the model and effort to set, and that switching mid-conversation
wipes the prompt cache. Current guidance: Opus 5 high effort where limits allow, because the
work is noticing that a passing test proves nothing and that a rule figure is invented.
Sonnet 5 is adequate for board management, ticket writing and Claude Code prompts; escalate
to Opus for any diff touching `rules/`, `contracts/` or `datasets/`.

**PROMPT 1 — identity and operating contract.** The one from `Prompts_Claude_Build.md`,
verbatim. It does not change. Add one line to it: *"Also read HANDOFF-PROTOCOL.md — it tells
you how to run the handoff when I ask for one, without me explaining it."*

**PROMPT 2 — context load.** Reading order, which file wins on which kind of disagreement,
any corrections to stale documents, and the standing constraints in full. Ends with:
*"Reply with three lines only: where we are, the exact next action, and what's at risk."*

**PROMPT 3 — standing orders.** From `Prompts_Claude_Build.md` PROMPT 7, amended for whatever
has changed — connector state, ticket conventions, the review loop.

**PROMPT 4 — verification, then work.** Three questions answerable only from the handoff, and
they must be *specific*, not thematic. Good: *"why doesn't `contracts.RuleDefinition` hold the
structured `RuleCondition` union?"* Bad: *"what did we decide about contracts?"* If the new
chat can't answer all three without searching again, the handoff is thinner than it looks and
that is worth knowing in the first five minutes rather than at a demo.

Then the first real task, named.

---

## The PR review loop — restate this in every handoff

1. He gives a PR number. Give this command shape, with the real number substituted:

```
cd ~/NewProjects/26034 && gh pr checks 29; gh pr view 29 --json headRefOid,updatedAt -q '.headRefOid + "  " + .updatedAt'; gh pr diff 29 > /mnt/c/Users/drona/Downloads/pr29.md; wc -l /mnt/c/Users/drona/Downloads/pr29.md
```

2. **`.md`, never `.diff`** — project knowledge rejects `.diff`.
3. **`pr<n>.md`, then `-v2`, `-v3`.** Never overwrite.
4. **Always compare the head OID and the blob hashes before reviewing a rework.** Teammates
   have reported fixes four times when the diff was byte-identical.
5. Under ~300 lines, paste in chat instead.
6. Delete the files from project knowledge once the PR merges.

**Merge gate:** checks green · one module · in ticket scope · no migration · no auth change ·
no shared-contract change · no new dependency. Otherwise escalate. Failed review gets a
comment listing specific fixes — never fix it yourself.

---

## Standing session hygiene

- Flag once when the conversation passes turn 30, again near 40.
- Flag immediately on repeating a point, forgetting a decision, or re-asking something
  answered. That is the trigger to run this protocol, not a warning.
- Say when something would be cheaper done another way: editing a message rather than
  correcting it, restarting from an earlier point, or moving the work into Claude Code.
- Do not wind down, summarise, or move toward a finale until he says explicitly that there
  are 24 hours left.
