# Rollover Promotion

Prod moves onto the dev branch, and dev moves onto a newly cut branch. Nothing is
merged between product branches. The images already exist: every product pipeline
publishes `<image>:<branch>`, and the infra/central deploy picks the tag from two
project variables in `infra/central`:

| Variable | Read by | Visibility |
|---|---|---|
| `CURRENT_RELEASE_BRANCH_PROD` | `production-on-prem` | protected branches only |
| `CURRENT_RELEASE_BRANCH` | `dev-on-prem` | every branch |

When the `_PROD` variable is visible it wins (`__get_envvar` in `central/iaas.py`).
A rollover is therefore: cut the next dev branch everywhere, then point each
variable at its new branch and deploy, dev first and prod second.

**Branch names move every release.** Below, `central-N` is the dev branch being
promoted, `central-N+1` the branch being cut, and `central-N-1` the prod branch
being retired. Read the actual names from the variables and the branches at the
start of each rollover (step 2). Never copy them from an earlier release: if today
prod / dev / next is 2.9 / 2.10 / 2.11, the release after that is 2.10 / 2.11 / 2.12. In commands,
`<N>`, `<N+1>` and `<N-1>` stand for those full branch names, and `<project>` is a
URL-encoded GitLab path such as `central%2Frest-api`.

## Gates

Steps 3, 4, 5 and 6 and a rollback push branches, change shared CI settings or
deploy. Each one needs the operator's go-ahead, given after they have seen the plan
from step 2. Never run a step they did not approve, and never run two steps on one
approval unless they approved them together.

Changing a variable needs Maintainer on `infra/central`. glab setup and pipeline
watching are in **Watching the Pipelines** in SKILL.md. The `ci_watch.py` target
for deploys is `infra/central`.

## Order

- Step 3: cut `central-N+1` and build its images.
- Step 4: switch dev to `central-N+1`, deploy `dev-on-prem`, and check that dev
  works.
- Step 5: only then switch prod to `central-N`, deploy `production-on-prem`, and
  check that prod works.
- Step 6: run the data steps.

Dev goes first so that the new branch's images and the deploy are proven on dev
before prod moves. A dev problem stops the rollover before prod is touched.

## 1. Preconditions

- The notes entry for `N-1..N` is published and accepted (R1). Notes written after
  the cut need the explicit pair (see **Ordering Is Not Negotiable** in SKILL.md).
- The operator has settled the go/no-go items the notes run raised (known gaps,
  deploy order, data steps).

## 2. Plan (read-only, then stop)

Gather all of this and show it before anything changes:

1. **Branch names.** Read the current values of both variables (item 8). Anchor
   on prod: its value is `central-N-1`, and `central-N` / `central-N+1` are the
   next two minor versions. The state then tells where the rollover stands:
   - Dev on `central-N` and no `central-N+1` branch: a fresh start.
   - Dev on `central-N` and `central-N+1` exists: resume at step 3, which skips
     branches already at the planned SHA, or at step 4.
   - Dev on `central-N+1`: resume at step 5.

   A prod value of `central-N` with dev on `central-N+1` means step 5 item 2 has
   run: anchor N on dev instead (`central-N+1` = dev's value) and resume at step 5
   item 3. Check that the two highest `central-*` branches in GitLab fit the state.
   Any other combination: stop and ask.
2. **Projects to cut.** Every GitLab project with a `central-N` branch, read from
   GitLab and not from local clones. A project nobody has cloned still ships an
   image. List the candidates with
   `glab api --paginate "projects?membership=true&archived=false&simple=true&per_page=100"`,
   then check `projects/<id>/repository/branches/<N>` for each one (404 means no
   branch). Record the tip SHA (`.commit.id`). The cut pins to it. Also check for
   `central-N+1`. If it already exists, record its SHA.
3. **Tip pipelines.** For each tip, read the status from
   `projects/<project>/pipelines?ref=<N>&sha=<tip>`. Prod will pull `:central-N` as
   the last green pipeline published it. A tip that is red or still running means
   the tag holds an older build, so it is a stop item.
4. **Commits on `central-N` after the entry was published.** Read them with
   `projects/<id>/repository/commits?ref_name=<N>&since=<publish time ISO>&first_parent=true`.
   First-parent lists merges by the time they landed. After the switch, prod runs
   the tip, so these commits ship without having been in the notes. List them per
   project for the operator to decide.
5. **Prod content the dev branch lacks.** A merge promotion keeps hotfixes pushed
   straight to `central-N-1`. A rollover drops them. For each project, in a fetched
   clone, run
   `git diff --quiet origin/<N> $(git merge-tree --write-tree origin/<N> origin/<N-1> | head -1)`.
   A diff, or a non-zero `merge-tree`, means `central-N-1` carries something that
   `central-N` does not. Don't count with `rev-list <N>..<N-1>`: earlier merge
   promotions left merge commits there, so that count is never zero.
6. **Images with no branch to cut.** On `dev-on-prem` in `central`, find every
   image tagged with the release branch: the `getattr(self, 'image_tag',
   get_current_release_branch())` and `self.release_branch` uses. Match each image
   to its project. If its project has no `central-N` branch, no pipeline will give
   the image a `:central-N+1` tag. List it: its tag has to be copied in Harbor
   (step 3), or the dev deploy cannot pull it. An explicit `image_tag` override is
   pinned and does not move with the rollover.
7. **Infra range and variables.** Run `promote.sh --check central`. It fetches,
   then prints `production-on-prem..dev-on-prem` with its tickets and preflight.
   Then diff the variable reads between the two branches, compare them with the
   `infra/central` variables, and list any variable prod does not define:
   - A missing `os.environ[...]` or `__get_required_envvar(...)` read fails the prod
     deploy.
   - A missing `__get_envvar(...)` read deploys the literal value `"unknown"`.
8. **Current variable values.** Read back each one with
   `glab api "projects/infra%2Fcentral/variables/<KEY>" | jq '{value, protected, environment_scope}'`.

Then stop and wait for the operator.

## 3. Cut `central-N+1` and build its images

This is safe before anything switches, because dev still reads `central-N`.

```bash
glab api -X POST "projects/<project>/repository/branches" \
  -f branch=<N+1> -f ref=<central-N tip SHA from the plan>
```

Create the branch in every project from the plan, pinned to the planned SHA, so
that what gets cut is what the operator saw. A project whose `central-N+1` already
sits at the planned SHA is done: skip it. One at any other SHA goes back to the
operator. This also makes the step safe to re-run after a partial failure.

Each new branch starts a pipeline that builds the `:central-N+1` images. Watch each
one to green, with one watcher per pipeline (R10). If no pipeline appears for a
branch, start one:
`glab api -X POST "projects/<project>/pipeline?ref=<N+1>"`.

For each branchless image from the plan, copy its `:central-N` tag to
`:central-N+1` in Harbor (`scr.syneto.eu/harbor/central-infra/<image>`). Harbor
needs the operator's credentials. If this session has none, hand the operator the
list.

## 4. Switch dev and check it

Only after every step 3 pipeline is green and every Harbor tag exists.

```bash
glab api -X PUT "projects/infra%2Fcentral/variables/CURRENT_RELEASE_BRANCH" -f value=<N+1>
glab api "projects/infra%2Fcentral/variables/CURRENT_RELEASE_BRANCH" | jq '{value, protected, environment_scope}'
glab api -X POST "projects/infra%2Fcentral/pipeline?ref=dev-on-prem"
```

The read-back must show `value` = `<N+1>` and `protected` still `false`, since every
branch reads it. If the key has several environment scopes, the PUT needs
`-f "filter[environment_scope]=<scope>"`.

Watch the pipeline the POST returned to green. Then check that dev works:

- Every product pod runs its `:central-N+1` digest as Harbor holds it after step 3
  (copied tags included), is ready, and has not restarted. Images pinned by an
  `image_tag` override (plan item 6) keep their pinned digest.
- The dev UI and API answer.

Dev now runs `central-N+1`, so feature work moves there from this point. Tell the
team now, not after prod switches: a feature pushed to `central-N` in the gap
before step 5 would ship to prod without ever running on dev.

Report the result and wait for the go-ahead for step 5. A dev failure stops the
rollover here: prod has not moved. To undo, set `CURRENT_RELEASE_BRANCH` back to
`central-N` and start the `dev-on-prem` pipeline again.

## 5. Switch prod and check it

1. **Re-check the tips.** Re-read each `central-N` tip and its pipeline status. If a
   tip differs from the plan, or its pipeline isn't green, go back to the operator
   with the new commits. Record each `:central-N` image's Harbor digest. Those are
   the digests prod must end up running.
2. **Set the prod variable and read it back:**
   ```bash
   glab api -X PUT "projects/infra%2Fcentral/variables/CURRENT_RELEASE_BRANCH_PROD" -f value=<N>
   glab api "projects/infra%2Fcentral/variables/CURRENT_RELEASE_BRANCH_PROD" | jq '{value, protected, environment_scope}'
   ```
   `protected` must still be `true`. An unprotected `_PROD` variable leaks into dev
   deploys and wins there. If the key exists under more than one environment
   scope, the PUT needs `-f "filter[environment_scope]=<scope>"`.
3. **Create the missing variables from the plan:**
   ```bash
   glab api -X POST "projects/infra%2Fcentral/variables" -f key=<KEY> -f value=<value> -f protected=true
   ```
   A value that only prod should see goes in as `<KEY>_PROD`.
4. **Bring infra prod up to date:**
   ```bash
   SYNETO_PROMOTE_CONFIRM=<N+1> promote.sh --push central
   ```
   After the cut, the gate wants the dev side of the derived product pair
   (`central-N+1`), even though only `central` is pushed. If the quorum guard
   refuses, step 3 is incomplete. Finish it first.
   - The push to `production-on-prem` **starts the prod deploy at once**:
     `update-infra` runs on every push. Items 2 and 3 run first so that this one
     deploy carries the new infra, the `central-N` images and every variable they
     need.
   - If the infra range is empty, `promote.sh` reports `NO-OP` and nothing deploys.
     Start the deploy by hand instead:
     `glab api -X POST "projects/infra%2Fcentral/pipeline?ref=production-on-prem"`.
5. **Watch the deploy and check prod.** The deploy pipeline is the id the manual
   POST returned, or
   `projects/infra%2Fcentral/pipelines?ref=production-on-prem&sha=$(git -C <root>/central rev-parse origin/production-on-prem)`.
   Watch it to green. Then check that prod works:
   - Each product pod runs the digest recorded in item 1, is ready, and has not
     restarted. Images pinned by an `image_tag` override keep their pinned
     digest.
   - The prod UI and API answer.

## 6. Data steps

Run the release items from the notes run that must happen after the deploy (settings,
roles, queue cleanups, scripts), each with its own go-ahead. They come from the
accepted entry, not from this skill.

## Afterwards

- **`central-N` is now the prod branch.** Every push to it rebuilds an image that
  prod deploys. Hotfixes go there. Anything that lands on `central-N` must also reach `central-N+1`, or the
  next rollover drops it.
- `central-N-1` is retired. The next release's notes and promotion derive
  `N..N+1` on their own.

## Rollback

A rollback is a deploy, so it needs the operator's go-ahead. First the operator
decides whether the old images can still run. If the `:central-N` images migrated
data, or step 6 has run, the `:central-N-1` images may not work against that data.
Then:

- **Infra merge stays:** set `CURRENT_RELEASE_BRANCH_PROD` back to `central-N-1`
  and start the `production-on-prem` pipeline.
- **Infra merge comes out too:** set the variable first, then revert the merge on
  `production-on-prem` with `git revert -m 1 <merge>` and push. That push is the
  deploy, so do not start one by hand. Never force-push.

The `:central-N-1` images are still in Harbor. Rolling dev back is in step 4.
