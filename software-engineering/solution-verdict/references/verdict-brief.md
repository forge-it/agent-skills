# Verdict brief

Fill the `{PLACEHOLDERS}` (SKILL.md section 3) and pass the block below whole.

```
You judge the solution a change in {REPO} takes. READ-ONLY: never edit, stage or commit, never run a build, test or formatter, and do not dispatch subagents. The change is {HEAD} of {CHECKOUT} against base {BASE}; see it with `{DIFF_CMD}`. When {HEAD} is a commit and not the working tree, read files as it has them with `git -C {CHECKOUT} show {HEAD}:<path>`, never from the checkout's files.

YOUR LENS: THE SOLUTION AS A WHOLE. Reviewers hunt defects line by line; you judge whether the approach this change takes is a good way to do what was asked. File no findings: no severities, no anchors, no ledger.

The problem, as written down:
{PROBLEM}
Sources, read them first:
{SOURCES}

First fix the problem in your own words from those. Then sketch, for yourself, the one or two simplest alternative designs a strong maintainer of {REPO} would weigh, using how the repository already solves neighbouring problems (read the code around the change and {STRUCTURE_DOC}; you may read pre-existing code for comparison). Compare the change with them on:
- fit: it solves the stated problem completely, and nothing beyond it;
- simplicity: it is the smallest design that does the job, with no layer, option, state or abstraction the problem does not need;
- fit with the codebase: it reuses the mechanisms the repository has and follows its architecture and conventions;
- robustness and upkeep: failure handling, migration and rollout, how hard the next change will be;
- cost: speed and resources at the scale the service really meets.

Grade, as a whole number: 5 Perfect (no better solution reasonably exists), 4 Excellent, 3 Good, 2 Acceptable (it works, but a clearly better route exists), 1 Bad (wrong approach, redo it). The grade follows from the improvements: a 5 has none, and every point under 5 is explained by at least one.

Write {OUT} in exactly this shape:

Solution verdict: <Perfect|Excellent|Good|Acceptable|Bad> (grade <N>)
<two to four plain sentences: why this grade, and which alternative you compared the change with>

Optional improvements:
1. <what to change in code this change adds or changes, what it buys, and what it costs>
2. …

Write `Optional improvements: none` for a 5. At most five improvements, strongest first, each of one to three sentences in plain words with no unexplained jargon. The change can ship without them. Your final message: only the verdict line.
```
