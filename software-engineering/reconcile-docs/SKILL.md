---
name: reconcile-docs
description: Guidelines for bringing project documentation back in sync with code after a change. Use after writing or changing code to decide whether and which docs (ADRs, API references, READMEs, roadmaps, gap entries) need updating — scoping the work strictly to what the diff actually touched. Project-agnostic across monorepos and single repos.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Reconcile Docs Skill

## Purpose

This skill provides guidelines for reconciling documentation with code after a change is complete. It decides **whether** documentation needs to change, **which** documents are in scope, and updates **only** what the change actually warrants. The default outcome is "no documentation change"; documentation is updated only when the change alters something a document describes.

This is invoked explicitly when wrapping up work — not on a fixed event. The scope of work may be a feature, a bugfix, a refactor, a one-line change, or closing a tracked gap. The skill must behave correctly for all of these.

## When to Apply

Apply these guidelines when:
- You have finished writing or changing code and want documentation to stay truthful
- A change may have altered a public contract, an architectural decision, setup/usage, or project direction
- A change implements something tracked in a gaps backlog that now needs closing

Do **not** apply when:
- There are no code changes (nothing to reconcile against)
- The change is purely a documentation edit already being made deliberately

## Core Principles

### 1. The Diff Decides Scope (CRITICAL)

Start from the actual set of changes, never from assumptions about what "should" have docs. Inspect the changed files first:

```bash
git status                 # uncommitted changes in the working tree
git diff                   # unstaged edits
git diff --staged          # staged edits

# Changes already committed on this branch, compared against the trunk you will
# merge into. Resolve the trunk from the remote's default branch — do NOT assume
# a local "main" exists or is current:
trunk=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
git diff "$trunk"...HEAD   # three-dot: diffs from the merge-base, so a stale/absent local trunk doesn't matter
```

Reconcile the **complete** set of changes that make up the work — including commits already on the branch, not just uncommitted edits.

**Determining the trunk robustly:** the integration target is whatever this branch will merge back into, not a hardcoded name. Prefer the remote default ref (`origin/HEAD`, which resolves to `origin/main`, `origin/master`, etc.). If `origin/HEAD` isn't set locally, `git remote set-head origin --auto` populates it. With no remote at all, fall back to the local default branch. The three-dot form (`<trunk>...HEAD`) diffs from the **merge-base**, so unrelated commits that landed on the trunk after you branched are correctly excluded — you see only what this work changed.

**The changed paths determine which documentation trees are even candidates.** A documentation tree whose corresponding code was not touched is out of scope. Do not open it, do not edit it.

In a monorepo this is the rule that prevents waste: if the diff contains no changes under `core/`, then `core/docs/` is irrelevant to this reconciliation — skip it entirely. Only the doc homes of *changed* areas, plus genuinely repo-wide docs (see Principle 4), are in scope.

### 2. Proportionality — Most Changes Need No Docs (CRITICAL)

Default to **no documentation change**. Most changes — internal refactors, small fixes, private renames, test-only edits — change nothing a reader of the docs would observe.

Update documentation only when the change alters something documentation actually describes:

- a public API, contract, schema, or wire format
- an architectural decision or a constraint
- user-facing behaviour, setup, or usage
- project direction or the status of a planned item
- a tracked gap that is now filled (or newly discovered)

If none of these apply, **state explicitly that no documentation change is needed** and stop. Do not invent an ADR, a changelog line, or a README paragraph to look thorough. Fabricated docs are worse than no docs.

### 3. Use the Navigation Map to Locate Doc Homes (HIGH)

Documentation layout is project-specific; discover it rather than hardcoding it. For each changed area:

1. Read the navigation file if present (`CLAUDE.md`, `AGENTS.md`, or equivalent) at the repo root and at the changed area's level — it usually states where docs live and how the repo is split.
2. Look for a `docs/` directory **at the changed area's level** and **at the repo root**.
3. Look for `README.md`, `ROADMAP.md`, and an ADR/decisions directory at those same levels.

`CLAUDE.md` is primarily a map you **read** to find doc homes — not a document you rewrite. Update it only when navigation, structure, or conventions themselves changed.

### 4. Match Documentation Layout to Repo Shape (HIGH)

**Monorepo with multiple services/packages:** each service may own its docs (e.g. `core/docs/`, `core/docs/api/`, `core/README.md`), and the repo root may hold cross-cutting docs (`docs/`, `README.md`, `ROADMAP.md`, `CLAUDE.md`).
- Reconcile a service's docs only when that service's code changed.
- Reconcile root-level docs only when the change affects repo-wide concerns (overall structure, cross-service contracts, top-level setup, project-wide roadmap).
- A change confined to one service must not drag in another service's docs or, usually, the root docs.

**Single repo:** the layout collapses to one `docs/`, one `README.md`, optionally `ROADMAP.md` and `CLAUDE.md` at the root. Same rules, one level.

### 5. Documentation Surfaces — What Each Is For (HIGH)

Walk the surfaces below for **in-scope areas only**, and change each only if its trigger is met:

| Surface | Update when… |
|---|---|
| **API reference** (e.g. `docs/api/`) | a public endpoint, contract, schema, or wire format changed |
| **ADR / decision record** | an architectural decision was made or revised — *new* ADR for a new decision; *status update* (superseded/accepted) for an existing one. Never for a mere implementation detail. |
| **README.md** (relevant level) | setup, usage, entry points, or the layout it describes changed |
| **ROADMAP.md** | the change completes, advances, or redirects a planned item |
| **Gaps backlog** (e.g. `docs/gaps/`) | the change fills a tracked gap (close it) or surfaces a new one (record it) — see Principle 6 |
| **Navigation** (`CLAUDE.md`) | structure, conventions, or where-things-live changed |

### 6. Close the Gaps You Fill (HIGH)

A gaps backlog (e.g. `repo/docs/gaps/`) tracks known shortfalls. When the diff implements something a gap entry describes, the reconciliation **must close that entry** using the repo's convention (mark resolved, move to a done section, or remove — match what the existing entries do).

Before closing:
- Verify the gap is **fully** addressed by the change. If only partially addressed, update the entry to describe the remaining work instead of closing it.
- If the change reveals a **new** gap, add an entry following the existing format.

Leaving a filled gap open is a defect; closing a gap that isn't actually fully addressed is worse.

### 7. Read Before You Write; Verify Before You Claim (CRITICAL)

Before editing any document, read it — match its existing structure, tone, headings, and formatting conventions. After editing, do not report a document as updated unless it actually is. "Docs reconciled" is a claim about the files on disk, not an intention.

### 8. New ADRs Record Human Decisions (HIGH)

An ADR captures a decision the human owns. When reconciliation implies a *new* ADR (a genuine architectural decision was made), draft it and confirm the decision and its framing with the user rather than silently committing prose that puts words in their mouth. Status updates to existing ADRs (e.g. marking one superseded by the change just made) can proceed directly.

## Anti-Patterns to Avoid

1. **Out-of-scope documentation**: editing the docs of an area the diff never touched (e.g. `core/docs/` when `core/` is untouched)
2. **Busywork docs**: inventing ADRs, changelog lines, or README prose for trivial or internal changes
3. **Orphaned gaps**: leaving a gap entry open after the change filled it — or closing one only partially addressed
4. **Blind edits**: editing a document without reading its existing format and conventions first
5. **Rewriting the map**: treating `CLAUDE.md` as something to rewrite rather than to navigate by
6. **Unverified claims**: reporting docs as reconciled without confirming the files changed
7. **Scope creep**: turning a small change's reconciliation into a broad documentation cleanup

## Guidelines

### Deciding Scope
- Begin with `git status` and `git diff` (working tree + branch commits)
- Derive the set of changed areas (services, packages, top-level dirs)
- For each changed area, locate its doc homes via the navigation file and by looking for `docs/`, `README.md`, `ROADMAP.md`, ADRs at that level
- Include root-level docs only for repo-wide effects
- Skip every area the diff did not touch

### Deciding Content
- Default to no change; require a concrete trigger (Principle 5) to edit a surface
- One change can touch several surfaces (e.g. an endpoint change → API reference + possibly an ADR + a closed gap)
- Keep edits proportional to the change

### Reporting
- State what was updated and **why**
- State what was deliberately left unchanged and **why** (e.g. "internal refactor, no observable behaviour — no docs needed")
- Flag any new ADR for confirmation before finalizing it

### Process Flow
```
1. git status / git diff        # complete change set (working tree + branch)
2. Derive changed areas         # which services / packages / dirs were touched
3. Read navigation (CLAUDE.md)  # at root and changed-area level → locate doc homes
4. For each changed area:       # in-scope surfaces only
     api/ · README.md · ADRs · ROADMAP.md · gaps/
5. Decide per surface           # trigger met? (default: no change)
6. Skip untouched areas         # e.g. core/ untouched → ignore core/docs/
7. Apply warranted updates      # read-before-write; close filled gaps
8. Report                       # updated (why) + left unchanged (why) + ADRs to confirm
```
