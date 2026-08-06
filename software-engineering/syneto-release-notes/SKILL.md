---
name: syneto-release-notes
description: Use when producing or publishing a Syneto Central release notes entry — a production hotfix or a major production release — including asks phrased as "release notes", "hotfix notes", "what is shipping", or when a central-2.x dev branch is about to be merged into the prod branch. Syneto-specific: assumes the Central repository family under /home/cristi/Projects and the CEN Confluence space.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.3"
---

# Syneto Release Notes Skill

## Purpose

Produce the release notes entry for a Syneto Central release and publish it to the
Confluence page, autonomously, from zero operator arguments.

The audience is stakeholders reading Confluence, not engineers. The entry describes
what a user can now do and what was broken and now works — never commits, files, or
internal jargon.

**Confluence page (the only format authority):**
`https://syneto.atlassian.net/wiki/spaces/CEN/pages/3932848142/Release+notes+-+plan`
cloudId `syneto.atlassian.net`, pageId `3932848142`.

## Position in the Release

```
syneto-release-notes  →  operator reviews the page  →  syneto-release-promote
```

This skill runs **first**, while the release is still unmerged. Promotion merges dev
into prod and empties the `prod..dev` range, after which the release can no longer
be described from git — `acquire.sh` reports every range as 0 and exits 1. That is
why the page is titled "Release notes - **plan**". Shipping is
`syneto-release-promote`, never this skill.

## When to Apply

Apply when asked to create, write, generate, or publish release notes for Syneto
Central — a hotfix or a major release.

Do **not** apply for:
- Release notes for any project outside the Syneto Central family
- SynetoOS appliance release notes (a different artifact entirely)
- Summarising a single branch or pull request

## Invocation Contract

The skill takes **no required arguments**. Everything resolves:

| Input | Resolution |
|---|---|
| Release type | Defaults to hotfix. Only a major release must be stated. |
| Date | Today. |
| Title | `Production Hotfix Plan (YYYY-MM-DD)` or `Production Release Plan (YYYY-MM-DD)` |
| Branch pair | Derived by numeric version sort (see R3). |
| Repositories | Discovered (see R3). |

Both titles already exist in the page history. Do not invent a new one.

## Stage Shape

```
acquire (shell, serial)  →  enrich (sonnet fleet, parallel)  →  synthesise (single agent, serial)  →  publish
```

**Acquisition is not agent work.** It is `git fetch` plus `git log` across ~16
repositories — deterministic, seconds of shell. Wrapping it in subagents buys
latency and nondeterminism and nothing else.

**Enrichment is the only stage that wants a fleet.** Roughly 40–50 unique tickets,
each an independent Jira fetch plus a rewrite into user-facing prose. Batch them:
about 6 tickets per sonnet subagent, not one agent per ticket.

**Synthesis must be single and serial.** Grouping several tickets into one entry,
assigning sections, and matching the tone of recent entries all require the whole
ticket set in one context. It cannot be split.

### Stage 1 — Acquire

`acquire.sh` sits beside this SKILL.md. Resolve its absolute path first — the
working directory when this skill fires is the operator's project, not the skill
directory, so a bare `./acquire.sh` will not be found.

```bash
/home/cristi/Projects/agent-skills/software-engineering/syneto-release-notes/acquire.sh
# optional explicit pair:  ... acquire.sh central-2.9 central-2.10
# offline dry run:         SYNETO_SKIP_FETCH=1 ... acquire.sh
# alternate checkout root: SYNETO_PROJECTS_ROOT=/path ... acquire.sh
```

**If it exits non-zero, stop. Do not publish. Report the stderr text.** The script's
header enumerates the causes — an already-merged release, a pair that fails the
quorum guard, a bad argument count, an unusable checkout root, and others. Read the
stderr text rather than guessing which applies. Standard output looks entirely
normal in every one of those cases; only the exit code distinguishes them.

The script self-documents its record format in the output header. Read every
bucket. `PAIR DOES NOT RESOLVE`, `RANGE READ FAILED`, and `FETCH FAILURES` are not
noise — they are the three ways a whole repository silently vanishes from a release.

### Stage 2 — Enrich

Take the union of the `TICKETS` records across all repositories. For each id, fetch
the Jira issue and return issue type, title, status, and a user-facing summary drawn
from the description and acceptance criteria — **not** from the commit message.

`XREF` records are cross-references to other tickets, not release content, and are
excluded (R5). Track which repositories carried each ticket **in a subject** — that
set becomes the bracket.

### Stage 3 — Synthesise

Fetch the Confluence page as HTML. Read the **top three entries** for format, tone,
and detail level. Harvest every ticket ID already published anywhere on the page —
that list drives R6.

Then group, classify, and write (R4, R5, R7).

### Stage 4 — Publish

`updateConfluencePage` requires the **entire** body on every write — there is no
append or patch mode, and `body` is a plain string parameter. The whole body
therefore passes through context once on the way back out. That single pass is
unavoidable; the job is to make it as safe as possible and to add no further passes,
because each intermediate copy retypes the bytes again without adding any guarantee.

```
1. Reuse the HTML body already fetched in Stage 3. Do not fetch the page again.
2. Emit the body once, unchanged except for the new entry: insert it immediately
   after the closing </p> of the intro paragraph, and give the new entry its own
   trailing <hr> so the previously-top entry keeps its separator.
3. Write with contentFormat "html" and
   versionMessage "automated release notes <date>".
4. Re-read the page and verify (R8).
```

**Never run the body through an HTML parser.** BeautifulSoup, lxml, and html5lib all
corrupt this page: they decode `&#039;`, `&quot;` and `&amp;` into raw characters,
rewrite `<hr …>` as self-closing, and reorder the attributes on every card anchor.
lxml and html5lib additionally wrap the result in `<html><body>`, which the API
rejects outright. If you script the insertion, do plain string insertion at a
located offset.

**Preserve everything you did not write, byte for byte.** The page carries entity
escapes, a `<time datetime="…">` node, and a terminal `<p>` whose only content is a
zero-width non-joiner (U+200C). Every existing element carries a `data-local-id`:
keep those exactly as fetched, and emit **no** `data-local-id` on the new entry's
elements — Confluence assigns them.

Rollback is Confluence page history, which versions every update. A scratchpad copy
of the body adds a second full transcription and no safety; do not make one.

The page holds 2026 entries only; pre-2026 releases live on a separate archive page.
If the HTML fetch ever starts failing for exceeding the response limit, archive the
oldest entries again rather than falling back to a lossy format.

## Core Principles

### 1. Never Touch a Worktree (CRITICAL)

Read remote-tracking refs only. Never `checkout`, `stash`, `reset`, `merge`, `pull`,
or otherwise disturb a worktree. (`git fetch` and `git status` do write inside
`.git` — remote-tracking refs and the index stat-cache — which is expected; the
invariant is that no working file ever changes.) A dirty worktree is reported and
left exactly as it is; the operator decides what to do about it.

### 2. Fetch Before Reading (CRITICAL)

Stale remote-tracking refs are the single largest source of silently wrong release
notes; local refs routinely run weeks behind. `acquire.sh` fetches first and reports
each failure with its reason. A repository under `FETCH FAILURES` has an untrusted
range — say so rather than publishing it as fact.

### 3. Discover Repositories, Never List Them (CRITICAL)

A hand-maintained inclusion list is always wrong. Legacy `central-*` repositories
receive occasional commits, and at least one contributor (`backend-proxy`) is not
named `central-*` at all.

Discovery rule: a repository contributes when both `origin/<prod>` and `origin/<dev>`
resolve **exactly** and the range is non-empty.

Three traps, all handled by `acquire.sh` and all worth knowing:

- **Exact ref match, never glob.** `rest-api` carries an `origin/central-2.9-backup`
  branch that a glob would happily match.
- **Numeric version sort, never lexical.** `central-2.9` sorts *above* `central-2.10`
  as a string. Highest version is dev, next is prod.
- **A derived pair must hold across the fleet.** At a major rollover the first team
  to cut `central-2.11` would otherwise flip the pair for everyone, producing a
  one-repository release. The script aborts when the pair fails in more
  repositories than it resolves in.

Discovery has one real blind spot: a contributing repository carrying **no**
`central-<N>.<N>` refs at all cannot be found. `bi-tool` is the precedent — it is
bracketed in the published 2026-03-02 entry but holds only `origin/dev` and
`origin/master`. **`bi-tool` is out of scope** for both skills by decision; do not
add it, and do not treat R3 as a completeness guarantee for other such repositories.

`central` is the exception: the IaaC repository, no `central-2.x` branches, pair
fixed at `origin/production-on-prem..origin/dev-on-prem`, entries tagged
`[platform]`. Its range is **not** release-scoped — it accumulates everything
unpromoted and reaches further back than the product range, so cross-check its
tickets against already-published entries with extra care (R6).

A repository that has left the release train but still carries old
`central-<N>.<N>` refs goes in `retired_repositories` at the top of `acquire.sh`
(currently `central-vat-searcher`). Retired repositories are reported under
`EXCLUDED AS RETIRED` rather than dropped — an exclusion list is the one place this
skill accepts hand-maintained configuration, so it must stay visible in every run.

### 4. One Theme Per Entry, Not One Ticket (CRITICAL)

Several tickets delivering one user-visible capability become **one** entry, with
every contributing ticket in the trailing bracket. The 2026-05-13 entry folds four
tickets — SYN-2151, SYN-2152, SYN-2153, SYN-2154 — into a single paragraph.

Conversely, one ticket touching four repositories is still one entry. The bracket
lists every repository that carried a non-skipped commit for it, comma-separated,
led by the repository owning the user-visible surface. The page fronts the repo a
reader associates with the change, not alphabetical order — `acquire.sh` emits
repositories alphabetically, so do not simply copy its order. Remaining repositories
follow in any stable order.

When a ticket spans `central` **and** product repositories, use the product
repository names and drop `[platform]`. `[platform]` applies only when `central` is
the sole contributor.

A contributing repository whose `TICKETS` record is empty produced only untagged
commits — `backend-proxy` is currently in this state with a single CI chore. It
yields no entry; note it in the provenance report rather than inventing one.

**Skip entirely:** revert pairs (cancel both), pure refactors, test-only changes,
doc edits, CI/tooling chores, and anything with no user-visible impact. If you
cannot tell, keep the entry and flag it in the provenance report rather than
guessing.

### 5. Ticket IDs: Subjects Only, SYN- and CENTRAL- Only (HIGH)

| Prefix | Meaning | Handling |
|---|---|---|
| `SYN-` | Jira, current tracker | Fetch via Atlassian MCP; inline card |
| `CENTRAL-` | YouTrack, legacy tracker | Not fetchable; plain link to `syneto.myjetbrains.com/youtrack/issue/<id>` |
| `DEF-`, `ADR-`, `MACHINE-` | External defect refs and in-repo document refs | **Not tickets.** Never fetch. |

A naive `[A-Z]+-[0-9]+` pattern will try to fetch `ADR-003` from Jira.

**Body-only ids are not release content.** An id appearing solely in a commit body
is nearly always a cross-reference to a *different* ticket that is not shipping
("parity with SYN-2346", "severity decisions belong to SYN-2398", "epic SYN-2514").
`acquire.sh` quarantines these in `XREF` records — deliberately not named
`TICKETS-something`, so that a `grep '^TICKETS'` cannot drag them back in.

**Cross-reference status is per-repository; the union of subjects wins.** The same
id can be a bare cross-reference in one repository and a real subject in another.
Build the union of `TICKETS` first, and treat as excluded only those ids that appear
in **no** repository's `TICKETS`. An id promoted this way is still subject to every
other rule — in particular, if its only subject is a doc-only or chore commit, R4
skips it regardless.

The bracket lists repositories where the ticket appears in a subject, never those
that merely mention it in a body.

### 6. Already-Published Tickets Are Excluded, Not Flagged (HIGH)

Hotfixes land on the prod branch and then re-land on dev, so they reappear in the
range on the next release. `SYN-2244` is an entire published entry from 2026-06-22
and is still sitting in today's range.

A ticket already published in an earlier entry is **excluded** from the new entry
and listed in the provenance report. Include it only when this release adds
materially new user-visible behaviour — and then say so explicitly in the entry
text.

The check covers this page. The pre-2026 archive page is deliberately not scanned.

### 7. Mirror the Top Three Entries (CRITICAL)

The format drifts. Read the top three entries each run and copy their current shape
rather than reproducing anything from this file:

- From 2026-03-02 onward the title is `<p><strong>Production Hotfix Plan (date)</strong></p>`.
- Older entries use `<h4><strong>…</strong></h4>`. Do not follow the older form.

Verified page structure, newest first, no `<hr>` between the intro and the top entry:

```
<p>intro…</p>
<p><strong>Production Hotfix Plan (2026-06-25)</strong></p>
<p><strong>Features:</strong></p>
<ul><li><p><strong>[repo, repo]</strong> text [<a …>card</a>]</p></li></ul>
<hr>
… next entry …
```

The only sections on the page are **Features** and **Bug Fixes**. Omit either when
it has no entries. Infrastructure work is not a separate section — it is a bracket
tag on an entry filed under whichever of the two fits. Use `[platform]`;
`[infrastructure]` appears once in older history for the same kind of work, but
`acquire.sh` only ever emits the `platform` tag, so keep to one form.

**Ticket links are inline cards, not markdown links.** The card is what renders the
ticket title and the live `Done` / `Testing` badge. In HTML the form is:

```html
<a href="https://syneto.atlassian.net/browse/SYN-2334" data-card-appearance="inline">https://syneto.atlassian.net/browse/SYN-2334</a>
```

Markdown round-trips the same node in a different representation. **Copy the exact
form used by the most recent entry on the page and substitute the URL** — do not
retype it from this file, and never invent `data-id` or other opaque id attributes;
the API rejects fabricated ids and only accepts ones copied from existing content.

**Never write the status text yourself.** `Done` and `Testing` are rendered by
Confluence from live Jira state. Writing them as literal text freezes a status that
will go stale.

### 8. Verify the Publish and Self-Report Failure (CRITICAL)

Publishing is autonomous, so verification is not optional. After writing, re-read
the page and confirm all three:

1. The new entry is present with the expected title and date.
2. Its ticket links rendered as `data-card-appearance="inline"` anchors, not plain
   links or raw text.
3. Nothing was clobbered: count the entry titles before and after, matching on
   title text rather than element — older entries use `<h4>` where newer ones use
   `<p><strong>`, so an element-based count silently ignores a third of the page.
   The count must be exactly one higher, and every pre-existing title must still be
   present with its original date.

If any check fails, stop and report loudly, naming the failed check. The prior state
is recoverable from the page's version history in Confluence, which is where the
operator restores from. Never retry a failed write blindly — a second bad write
buries the good version one step deeper in that history.

## Provenance Report

Reported **to the operator in the response, never written to Confluence**:

- The branch pair used, and whether it was derived or supplied
- Contributing repositories with commit counts
- Repositories under `PAIR DOES NOT RESOLVE`, `RANGE READ FAILED`, `FETCH FAILURES`
- Dirty worktrees, with contributing status
- Tickets that could not be fetched
- Tickets excluded as already published (R6)
- `XREF` ids and whether any were promoted to shipping (R5)
- Contributing repositories that yielded no entry (empty `TICKETS`, or all commits
  skipped as chores)
- Commits skipped as chores that a human might disagree with

## Entry Shape

Shown as markdown for readability. The published form is the HTML in R7 — this
sketch fixes the *content* shape only.

```
**Production Hotfix Plan (2026-08-06)**

**Features:**

* **[rest-api, central-backend]** <what the user can now do, where to find it, who
  benefits — UI paths included when the ticket mentions them> [<card>, <card>]

**Bug Fixes:**

* **[central-ui]** Fix bug where <symptom>; <resolved behaviour>. [<card>]
```

Bug fixes follow the established "Fix bug where X; now Y" formula. Features run one
to four sentences — long enough for a multi-ticket theme, trimmed ruthlessly
otherwise.

## Why the Log Recipe Looks Odd

The repositories mix GitLab merge commits with direct pushes to the release branch —
close to half of all landings are merges. Ticket IDs therefore live in both merge
subjects (`Merge branch 'SYN-2591-cross-tenant-authorization'`) and direct commit
subjects, which is why `acquire.sh` reads subjects from the **full** log including
merges, and takes descriptive content from `--no-merges`.
