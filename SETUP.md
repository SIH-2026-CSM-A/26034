# SETUP.md — 26034

Two parts. Part A is the project setup, mostly done. Part B is what **every teammate**
runs once on their own machine — that one is not optional and not done.

Delete Part A once every box is ticked. Keep Part B.

---

# PART A — project setup (Abhiram only)

## 1. Git and GitHub

- [x] Org `SIH-2026-CSM-A` created
- [x] Repos `26034` (public) and `26167` created
- [x] Ruleset `main-protection` on `main`: PR required, 1 approval, code-owner review,
      stale dismissal, linear history, no force push, no deletion, admin bypass
- [x] Classic rule restricting push to `main` to `Abhiram-0910` — this is what stops a
      teammate merging; the ruleset alone does not
- [x] Squash merge only, head branches auto-deleted
- [ ] CI added as a **required status check** on the ruleset — do this the moment
      VP-CI-001 merges and the check exists
- [ ] All eleven teammates invited to the org as Member, in team `Developers`
- [ ] CODEOWNERS line added for each teammate as their username arrives

## 2. Claude GitHub App

- [x] Installed on the **organisation**, scoped to `26034` only
- [x] `CLAUDE_CODE_OAUTH_TOKEN` secret set — subscription path, no API billing
- [x] `.github/workflows/claude.yml` — `@claude` on mention only
- [ ] Actor guard `github.actor != 'claude'` added to stop self-retriggering
      (included in VP-CI-001)

## 3. Ticket board

- [x] ClickUp list `26034 Build`, statuses `to do / doubt / in progress / review / done / complete`
- [x] Custom fields: Module (dropdown), Files (text), Branch (text)
- [ ] Status contract circulated to the team — who moves what, and when

## 4. Rule corpus

- [ ] Source gazettes downloaded and committed to `rules-corpus/`. `consumeraffairs.gov.in`
      blocks automated access, so this is a manual download, once, by hand. There is no
      scheduled-sync path — do not build a fetcher.
- [ ] Every encoded rule cites the gazette it derives from

## 5. Environment

```bash
cp bck/.env.example bck/.env
```

- [ ] `.env.example` lists every required variable
- [ ] `.env` is gitignored
- [ ] No secret appears anywhere in tracked files
- [ ] Cost ceilings set: Featherless token budget, Document AI daily page cap (default 0)

## 6. Docs

- [x] `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`, `TODO.md`, `SETUP.md` written
- [ ] `SESSION-LOG.md` left empty — the agents fill it
- [ ] `DESIGN.md` in `fnt/` before any component is built

---

# PART B — every teammate runs this once

Ten people, ten machines. Skipping any of these produces a broken PR that wastes
a review cycle.

## 1. Tools

```bash
# GitHub CLI
gh --version || sudo apt install -y gh
gh auth login          # GitHub.com -> HTTPS -> Y -> Login with a web browser

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- [ ] `gh auth status` shows your own account
- [ ] `uv --version` prints

## 2. Clone into the Linux filesystem

Not `/mnt/c/`. Git across the Windows mount is several times slower.

```bash
mkdir -p ~/NewProjects && cd ~/NewProjects
git clone https://github.com/SIH-2026-CSM-A/26034.git
cd 26034
```

- [ ] Cloned under your home directory

## 3. Commit identity — do this before your first commit

The repository is **public**. Author emails in commit history are scraped. Use your
GitHub no-reply alias, found at github.com/settings/emails.

```bash
git config user.name "Your Full Name"
git config user.email "ID+username@users.noreply.github.com"
git config --get user.email
```

- [ ] Email is the `@users.noreply.github.com` alias, not your personal address

Rewriting authorship later means force-pushing, and `main` rejects that.

## 4. Install and verify

```bash
cd bck
uv sync
uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest
```

- [ ] All four pass on a clean clone

If `lint-imports` finishes suspiciously fast, the package is not installed and it is
analysing nothing. Re-run `uv sync`.

## 5. Read before you write

- [ ] `AGENTS.md` — module ownership, the import rule, the constraints that never bend
- [ ] `ARCHITECTURE.md` — how it fits together
- [ ] Your ClickUp ticket — module, files you may edit, branch name, acceptance criteria

## 6. Your working loop

```bash
git checkout main && git pull
git checkout -b <branch-name-from-your-ticket>
# work, commit incrementally
git push -u origin <branch-name>
gh pr create --base main --title "<TICKET-ID>: <what>" --body "Closes <TICKET-ID>."
```

Then move your ticket to **review**. Do not merge — only Abhiram merges.

- [ ] You have opened one PR and had it merged, end to end, before real work starts
