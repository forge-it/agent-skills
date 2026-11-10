# The MR's mentoring section

The merge request is Cristian's mentoring gate: he reads what the junior understood beside
what changed. The description is the senior's stage 10 description (what changed and why, how
it was tested, the risk, the ticket link), dev to dev, and then this section. Write it with
the junior at stage I from `understanding.md`. It goes through the same WAF line check as the
rest of the description, and the template avoids the shapes that check blocks: never a word
followed by a space and `(`.

```text
## Mentoring

Session 7 · new this ticket: pytest.fixture, ddd.repository-port

| File | Written by | Explained back |
|---|---|---|
| src/tests/unit/licensing/test_activation.py | junior, by hand | yes |
| src/central_rest_api/application/services/activation.py | mentor, in session | partly: the commit inside the UoW |
| src/central_rest_api/domain/repositories/products.py | junior, via prompt | yes |

Stuck: ddd.repository-port — put SQL in the domain twice; a word from you would help.
Questions for your review: why does the fake repository not need `commit()`?
Docker tiers: integration, mentor-run: passed / not run.
```

- **Written by:** `junior, by hand`, `junior, via prompt` (the coder subagent from his prompt),
  `mentor, in session`, or `written by Claude, not explained back` when he skipped it with
  "just do it".
- **Explained back:** `yes`, `partly: <the gap>`, or `no` (a hunk still ✗ at stage G).
- Name every concept still `stuck`, his open questions and every test tier not run. Leave
  out what is fine, and any level change: that is between the junior and Cristian.

## Reading the review back (stage J)

Read Cristian's notes, in a review round and again after the merge:

```text
glab mr view <branch> -R <group>/<repo> --comments -P 100
```

The long flag, on purpose: this machine's `rtk` hook drops the comments from `-c` and still
exits 0. The `comments:` count in the header must match the number of notes you read.

For each comment: did it name a wrong belief or a missed rule (fill `misconception`; the
state per `learner-profile.md`'s table), confirm something (evidence), or answer one of his questions (a
`study-notes.md` tick or a glossary line)? Apply it per `learner-profile.md`, and note in
`retro.md` what Cristian corrected.
