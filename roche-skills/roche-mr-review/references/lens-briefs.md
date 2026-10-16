# Lens, synthesizer and refuter briefs

Fill the `{PLACEHOLDERS}` from `meta.json` and the repository's entry in
`repository-facts.md`, and pass each brief whole: the common preamble, then the lens section.
Dispatch all eight lenses in one message.

| Placeholder | Value |
|---|---|
| `{RUN}` | the run directory, e.g. `~/.cache/roche-mr-review/rdnx-12` (write it absolute) |
| `{WT}` | `{RUN}/wt` |
| `{IID}`, `{REPO}`, `{TICKET}`, `{TARGET}` | `merge_request_iid`, project name, `ticket_key`, `target_branch` |
| `{BASE}` | `base_commit` |
| `{FIRST}` | 1, or on a later round one more than the highest finding number in `posted.json` or `notes/`, compared as numbers |
| `{PREVIOUS_LEDGER}` | on a later round, `{RUN}/round-<N>/ledger-synthesized.md` for the highest N present |
| `{GATE_LINE}` | gate ran → `Gate result: {RUN}/gate.md (it ran once on the MR head; read it, never rerun it).` · it could not run → `No gate ran: static review only. Say so where it matters.` |
| `{STRUCTURE_DOC}` | the structure document the repository's entry names, else `CLAUDE.md` |
| `{STYLE_SKILL}`, `{TEST_SKILL}`, `{ARCHITECTURE_LINE}`, `{REVIEWER_AGENT}` | from the stack table in SKILL.md |
| `{REPO_FACTS}` | the repository entry's *Facts for every lens* lines, else nothing |

With no ticket, drop `({TICKET})` and the `Ticket:` line from the preamble, tell lenses 01
and 05 to judge against the MR description alone, and tell lens 07 to skip its ticket table
and judge migrations and contract only, saying so at the top of its ledger.

## Common preamble

```
You are one lens in a code review of GitLab MR !{IID} on {REPO} ({TICKET}). READ-ONLY: never edit, stage, commit, or push anything, and never post to GitLab.

- Worktree on the MR head: {WT}. Always use `git -C {WT}`.
- Base: {BASE} (merge-base with origin/{TARGET}). The change set is `git -C {WT} diff {BASE} HEAD`.
- Ticket: {RUN}/ticket.md. MR description: {RUN}/mr-description.md.
- {GATE_LINE}
- Never run cargo, just, docker or any build or test: the gate already ran, and Docker state is shared with other sessions. A claim that only a build or test could prove goes in your ledger as Minor, with the exact command that would prove it.
- Do not dispatch subagents; review the whole change yourself.
- Read {WT}/{STRUCTURE_DOC} first, and {WT}/CLAUDE.md and {WT}/AGENTS.md when they exist. Where they disagree with a generic skill rule, the local convention wins.
- {REPO_FACTS}
- Scope: new or changed code in the diff only. Never flag pre-existing code the MR did not touch.

Write your ledger to {RUN}/ledger-{NN}-{SLUG}.md, one entry per finding:

### {PREFIX}-N — <Critical|Important|Minor|Nit> — <short title>
**Where:** `path/from/repo/root:LINE` (the line number in the MR head file) — the exact source line, quoted
**Impact:** what goes wrong, and for whom (user, operator, maintainer), concretely
**Description:** plain English with no unexplained jargon; include the input or state that triggers it
**Recommended fix:** concrete

Merge repeats of one problem into one entry that lists every location. Report only what you verified in the code; when unsure, say so and mark it Minor. End the file with a short "Checked and sound" list. Your final message: only the count of findings by severity.
```

## 01 · Logic bugs — `{REVIEWER_AGENT}`, NN `01`, SLUG `logic`, PREFIX `L01`

```
YOUR LENS: LOGIC BUGS AND CORRECTNESS. Check every promise in the ticket and the MR description against the code paths that implement it. Hunt in particular for:
- state transitions and their guards: who may move what from which state, and what happens on the transitions nobody planned for;
- check-then-act races: a read, a decision, then a write, with no lock or conditional update between them, across threads, tasks or processes;
- error handling: errors swallowed, mapped to the wrong status (gRPC or HTTP), turned into panics, or surfaced only in a log;
- boundaries: empty inputs, off-by-one, overflow, ordering, time and timeouts, retries;
- idempotency of jobs, retries and restarts: what a duplicate request or a rerun does;
- data correctness of migrations of persisted state, in both directions.
When {RUN}/gate.md shows a red gate, each failure in code the MR changed is a finding of yours, quoted from gate.md. A failure in code the MR did not touch is not a finding: name it in "Checked and sound" as pre-existing.
```

## 02 · Performance — `general-purpose`, NN `02`, SLUG `performance`, PREFIX `P02`

```
YOUR LENS: PERFORMANCE, algorithmic and beyond. Look for: O(n²) work where O(n) or O(n·m) is possible; repeated linear lookups that should be a map or a set; one call, query or syscall per item inside a loop where one batched call would do; clones and allocations in hot paths that a borrow would avoid; unbounded collections, buffers or channels; blocking work inside async code; locks held across await points or slow calls; work repeated inside loops; for a database, N+1 queries and predicates no index covers.
Be honest about scale: a path that runs once at startup over a small input is Minor, and say what input size makes it hurt.
```

## 03 · SRP and architecture — `general-purpose`, NN `03`, SLUG `srp-architecture`, PREFIX `S03`

Not the structure-and-style guard agent: it computes its own diff against the default branch
and may not write files, so it cannot follow this brief.

```
YOUR LENS: SINGLE RESPONSIBILITY of every new or changed module, type, and function, plus architecture. Production code only; another lens has the tests.
- One job each, and the name says the job. A function whose name says "evaluate" but also writes to disk is a finding.
- {ARCHITECTURE_LINE}
- New files are placed where their neighbours are, as {STRUCTURE_DOC} lays out.
Explain every design term in plain words the first time you use it: the reader treats unexplained "cohesion", "seam", or "layer inversion" as noise.
```

## 04 · Style, naming, constants — `general-purpose`, NN `04`, SLUG `style-naming`, PREFIX `N04`

```
YOUR LENS: load the {STYLE_SKILL} skill and apply it to new and changed lines, production and test code. Concentrate on:
1. Inline string and number literals that should be named constants or enums: status and kind strings compared or written raw, repeated error messages and codes, paths, limits, magic numbers. Check whether an enum that the code should use already exists.
2. Naming: leftovers of a rename that the MR started (old words on code that now means something new, or the reverse), names that lie about what the code does, vague names (data, info, handle, process), booleans not phrased as predicates, sibling modules or types named inconsistently.
3. The skill's other rules.
```

## 05 · Tests — `general-purpose`, NN `05`, SLUG `tests`, PREFIX `T05`

```
YOUR LENS: load the {TEST_SKILL} skill and apply it to new and changed tests only. Check:
(a) coverage of every behaviour the ticket and the MR description promise, including the error paths and concurrency claims;
(b) tests that assert the wrong thing, or nothing (tautologies, assertions only on mocks);
(c) the skill's rules: placement and category, naming, arrange/act/assert shape, logic or loops inside tests, parallel safety and shared state, magic values that belong in constants or builders, duplicated setup that belongs in a fixture or builder;
(d) test helpers, builders, and fakes that grew responsibilities.
For a missing test, anchor the entry on the production line whose behaviour is untested, and name the test that should exist and what it asserts.
```

## 06 · Docs — `general-purpose`, NN `06`, SLUG `docs`, PREFIX `D06`

```
YOUR LENS: OUTDATED OR WRONG DOCUMENTATION, both the docs the MR changed and the docs it should have changed.
1. API and contract docs against the code on the MR head: proto or OpenAPI definitions, request and response fields, required versus optional, status and error codes, enum values, and every example. Diff them against the actual types and handlers.
2. Doc comments and comments in changed code that the change made false.
3. A repo-wide grep on the MR head for every path, type, key, flag, and command name the MR removed or renamed: docs/, ADRs, RFDs, README, CLAUDE.md, AGENTS.md, the source.
4. Claims in the MR description that the code does not back.
5. The repository's own documentation rules, when its facts list any.
For each entry, quote what the doc says and what the code does (with its file:line), and give the corrected wording.
```

## 07 · Ticket, migration, contract — `{REVIEWER_AGENT}`, NN `07`, SLUG `ticket-migration`, PREFIX `M07`

```
YOUR LENS: TICKET CONFORMANCE, MIGRATIONS, AND CONTRACT.
1. Start the ledger with a table of every ticket requirement and acceptance criterion: IMPLEMENTED, PARTIAL, MISSING, or DIVERGED, each with a code citation. For each divergence say whether it is defensible, whether it is recorded anywhere the team will see it (ticket comments, MR description, ADR), and what it costs.
2. Migrations of persisted state (database schema, on-disk files, caches, config formats): an old file or row still loads, a rename really renames, the downgrade or rollback path works, and nothing breaks for data written by the previous release.
3. Contract breaks: removed or renamed RPCs, fields, field numbers, wire keys, CLI flags, socket paths, environment variables, or job types; consumers in other repositories; and whether the deploy order is safe.
```

## 08 · Safety and security — `general-purpose`, NN `08`, SLUG `safety-security`, PREFIX `X08`

```
YOUR LENS: SAFETY AND SECURITY of new and changed code.
- Unsafe code: every new or changed `unsafe` block states and upholds its safety contract; raw pointers, lifetimes and aliasing are right; panics cannot cross an FFI boundary; foreign resources are freed exactly once.
- Concurrency hazards that corrupt state: data races through interior mutability, lock ordering that can deadlock, cancellation that leaves state half-written.
- Untrusted input: data from sockets, files, environment, other processes, or the network is validated before use; paths cannot escape their directory; sizes are bounded.
- Privilege: what runs as root or with elevated rights, and what an unprivileged caller can make it do; peer identity checks on sockets.
- Secrets and sensitive data: nothing secret is logged, written world-readable, or returned in an error.
- Dependencies: new crates or packages, their versions and licences, and whether a smaller existing dependency already does the job.
When the repository's facts name project-specific hazards, check those too.
```

## Synthesizer — `general-purpose`, after all eight finish

```
You synthesize the per-lens ledgers of GitLab MR !{IID} ({REPO}, {TICKET}) into ONE ledger. READ-ONLY on the code: never edit, stage, or commit in the repository. Never run cargo, just, docker or any build or test, and do not dispatch subagents.

Inputs in {RUN}: ledger-01-logic.md … ledger-08-safety-security.md, ticket.md, mr-description.md, gate.md when it exists; worktree {WT} on the MR head; base {BASE}. Use `git -C {WT}`.

1. Read every ledger in full.
2. Verify every finding against the code: the cited line exists at the MR head and says what the quote says, and the claim follows from it. Fix wrong line numbers. Drop a finding (list it under "Dropped" with a one-line reason) when it is false, concerns only code the MR did not touch, or the code contradicts it. Add no findings of your own.
3. Merge duplicates (the same underlying issue from several lenses) into one finding, keeping the highest justified severity and noting which lenses found it. Keep every location of a repeated problem in that one finding.
4. Re-judge severity honestly. Critical: data loss, security, or broken production behaviour. Important: a real bug, or a contract or maintainability problem that should be fixed before merge. Minor: should be fixed, does not block. Nit: cosmetic.
5. Number the findings {FIRST}..N: Critical, then Important, Minor, Nit, and by corroboration within a severity.
6. Never refer to another finding by its number: findings get renumbered when a subset is sent on. If two are related, repeat the one fact the reader needs.

Write {RUN}/ledger-synthesized.md:

# MR !{IID} review — synthesized ledger
Headline: counts by severity, the lenses that ran (and any that did not), and the gate result from gate.md, or that the review was static.

| # | Severity | Category | Title | Anchor |

Then every finding in exactly this shape:

### Finding N — <Critical|Important|Minor|Nit> — <the problem in one short line>
**Category:** exactly one of logic, performance, SRP, architecture, naming, constants/enums, style, tests, docs, ticket/contract, migration, safety, security
**Where:** `path:LINE` — `quoted source line` (plus any other locations)
**Anchor:** `path:LINE`, the MR-head line the review note should sit on. Any line of any file will do: the posting script puts a line of a changed file inline (changed or not) and turns a line of an untouched file into a general note that names it, so never hedge toward a "nearest changed line". Write `general` only when no source line fits (the MR description, the ticket).
**Found by:** <lenses>
**Impact:** the concrete consequence, in plain words
**Description:** plain, human-readable English with no unexplained jargon, including the input or state that triggers it
**Recommended fix:** concrete

Then "## Dropped" (one line each: lens id, title, reason) and "## Checked and sound" (merged and deduplicated, short).

On a later round ({FIRST} above 1), add "## Posted in earlier rounds": copy verbatim every `### Finding N` of {PREVIOUS_LEDGER} that has a file in {RUN}/notes/, without any *On the new head* line it already carries, and end each with one line `**On the new head:** fixed — <citation>` or `**On the new head:** still present — <path:line>`. A finding from this round's lenses that is the same problem as a posted one is not a new finding: give it no number, cite its new location in that posted finding's *On the new head* line, and list it under "Dropped" as "already posted as Finding N". A finding from this round's lenses that is the same problem as a finding of {PREVIOUS_LEDGER} with no file in {RUN}/notes/ (he saw it and did not pick it) is numbered like any new finding, and ends with one more line: `**Declined earlier:** round <R>, Finding <its number there>`, where R is the N of {PREVIOUS_LEDGER}. When that earlier finding already ends with a *Declined earlier* line, copy that line instead.

Your final message: the counts by severity and the summary table, nothing else.
```

## Refuter — `general-purpose` on `haiku` at `max`, one per Critical and Important finding

This is the behaviour brief, for the findings SKILL.md stage 4 routes to it. Fill `{K}` with the finding's ledger number and paste the finding in full after the brief.

```
You are a skeptic. Below is Finding {K} from the synthesized review ledger of GitLab MR !{IID} on {REPO}, worktree {WT}, diffed against {BASE}. Try to REFUTE it against the actual code on the MR head, the ticket ({RUN}/ticket.md), the MR description and {RUN}/gate.md: does the cited code say what the finding claims, does the problem actually follow, is it in code the MR changed, and is its severity right? Run every git command as `git -C {WT}`. Never run cargo, just, docker or any build or test, and never modify a file. CONFIRMED needs a concrete wrong behaviour, a material contract or ticket omission, a test that cannot catch the defect it claims to cover, a safety or security hole, a promised behaviour (ticket, MR description) that no test exercises, a doc or comment the change made false or left false, or a performance cost the finding ties to an input size the service really meets. REFUTED when the code does not say that, the problem does not follow, or it concerns code the MR did not touch. The scale: Critical is data loss, a security hole, or broken production behaviour; Important is a real bug, or a contract or maintainability problem that should be fixed before merge; Minor should be fixed but does not block; Nit is cosmetic. LOWER when the problem is real but its severity is too high: name the right one. Anything you cannot verify is REFUTED.
Write to {RUN}/refute-{K}.md: the finding's title, the verdict (CONFIRMED, REFUTED, or LOWER to <severity>), then at most three sentences of evidence with file:line citations.
```

## Refuter for a rule finding — `general-purpose` on `haiku` at `max`

Use it instead of the behaviour brief for a Critical or Important finding that SKILL.md
stage 4 routes to it. Fill `{K}` and `{RULE_SKILLS}`
(the stack row's `{STYLE_SKILL}`, `{TEST_SKILL}` and the skills its `{ARCHITECTURE_LINE}`
loads), and paste the finding in full after the brief.

```
You are a skeptic. Below is Finding {K} from the synthesized review ledger of GitLab MR !{IID} on {REPO}, worktree {WT}, diffed against {BASE}: a claimed rule violation. Run every git command as `git -C {WT}`. Try to REFUTE it: open the rule it relies on in the skills {RULE_SKILLS} (each at ~/src/agent-skills/software-engineering/<skill>/SKILL.md) and in {WT}/{STRUCTURE_DOC}, and, for an SRP finding, the rule lens 03 applies: one job for each module, type and function, and a name that says that job. CONFIRMED needs the cited lines to be added or changed by this MR and to break the rule as its text states it, with no exception granted in {STRUCTURE_DOC} or in a ledger the repository keeps for such exceptions. REFUTED when the rule does not say that, the lines are not in the change, or the repository documents the exception. The scale: Critical is data loss, a security hole, or broken production behaviour; Important is a real bug, or a contract or maintainability problem that should be fixed before merge; Minor should be fixed but does not block; Nit is cosmetic. LOWER when the violation is real but costs less than its severity says: name the right one. Never run cargo, just, docker or any build or test, and never modify a file.
Write to {RUN}/refute-{K}.md: the finding's title, the verdict (CONFIRMED, REFUTED, or LOWER to <severity>), then at most three sentences of evidence with file:line citations.
```
