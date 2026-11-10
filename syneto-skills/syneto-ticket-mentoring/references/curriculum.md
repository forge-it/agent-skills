# Curriculum

The concepts a junior meets on Syneto tickets, as stable ids for `profile.md`. This is a map,
not a course: nothing here is taught until a ticket needs it.

Each line: `id` — what it means — **P** (first ticket, at the step that first needs it) or **J** (later tickets, when one touches it) — the act that proves it
(introduced → practised).

The areas are in the order a rest-api ticket meets them.

## sh. Terminal and machine

He has used a shell for test setups: name what he already does before adding to it.

- `sh.paths` — absolute vs relative paths, `cd`, `ls`, `cat`, `~` — P — finds a file by path without help
- `sh.read-vs-write` — a command that reads (status, diff, `--check`, `--no-fix`) vs one that rewrites — P — says which a command is before running it
- `sh.venv-python` — the repository's `.venv/bin/python`, never bare `python`; why a venv — P — runs a test with the right interpreter
- `sh.git-dash-c` — `git -C <repo>` and why the working directory matters — P — uses it unprompted
- `sh.env-file` — environment variables, `.env`, why it is never printed — J — explains where a setting comes from
- `sh.docker-lock` — containers, `docker compose up/down`, the lock and why the machine is shared — J — runs a Docker tier under the lock and brings it down
- `sh.port-check` — `lsof -i tcp:<port>`, a port held by a process — J — finds what holds a port

## git. Git

A reproduction is a story in steps; so is a commit history.

- `git.status-diff-log` — `status --short`, `diff`, `log --oneline`: where am I, what changed — P — reads his own tree's state aloud
- `git.branch-from-base` — the base branch, pull first, branch from it; why never from a stale base — P — types the sequence
- `git.never-rewrite` — never stash, reset, force, clean: they destroy someone's work — P — says why when asked
- `git.add-by-path` — staging named files, never `-A` — J — stages exactly the ticket's files
- `git.commit-message` — the repository's subject shape, the ticket key, a body that says why — J — writes an accepted message
- `git.push-and-mr` — push, the merge request, its target branch, the review — J — opens an MR via the senior's stage 10
- `git.squash-merge` — what squash did to his commits; why local branches look unmerged — J — explains the `sha` check at cleanup

## py. Reading Python

He reads logs and stack traces already: start from a stack trace.

- `py.stack-trace` — reading a traceback bottom-up to the first frame in our code — P — finds the failing line in a traceback
- `py.module-import` — module, package, absolute import, where a name comes from — P — follows an import to its file
- `py.function` — parameters, return value, call — P — predicts a function's return for an input
- `py.class` — class, instance, method, `self` — P — says what an instance holds
- `py.type-hints` — annotations as documentation the type checker enforces — J — reads a signature correctly
- `py.dataclass` — `@dataclass` as a record with fields — J — predicts the generated `__init__`
- `py.exceptions` — raise, except, a domain error vs an HTTP error — J — traces where an exception is caught
- `py.enum` — `StrEnum` and closed sets — J — uses an enum member instead of a string
- `py.comprehension` — list and dict comprehensions — J — rewrites a loop as one, or reads one aloud
- `py.decorator` — a function that wraps a function; FastAPI routes — J — says what a route decorator registers
- `py.context-manager` — `with`/`async with`, setup and guaranteed teardown — J — says when the block's resource is released
- `py.async-await` — coroutines, `await`, why a handler is `async def` — J — says what runs while one request awaits
- `py.protocol` — `Protocol` and ABC as a contract without an implementation — J — finds a port's implementations

## pyw. Writing Python, the house way

The house skills are review checklists, opened while reviewing: **python-code-style**,
**python-testing**, **python-ddd**. Cite their rule numbers as they spell them.

- `pyw.naming` — no single letters, no abbreviations, a name says its job (the senior's `references/naming-guide.md`) — P — names a variable and a function acceptably unaided
- `pyw.house-deviations` — no `-> None`, truthiness over `is None`, docstrings only for the why: deliberate, not mistakes — J — leaves them as they are in review
- `pyw.constants-enums` — constants at module top, enums for closed sets — J — applies it in his diff
- `pyw.composition` — composition over inheritance — J — explains a composed class
- `pyw.minimal-comments` — the code says what, a comment only says a non-obvious why — J — deletes a narrating comment

## pytest. Tests

His biggest asset: a test case is arrange, act, assert; a repro is a failing test; boundary
cases are his habit. He writes tests before he writes production code.

- `pytest.assert` — `assert` with a message, what a pass and a failure look like — P — writes an assert that fails for the right reason
- `pytest.run-one` — running one test by its id — P — runs one test unaided
- `pytest.read-failure` — reading pytest's failure output: expected vs actual, the frame — P — names the cause from the output
- `pytest.naming` — a test name states the behaviour, not the steps — J — names a test acceptably
- `pytest.fixture` — fixtures as arrange steps, their scope — J — writes a fixture
- `pytest.conftest-layering` — which `conftest.py` provides what; support modules — J — finds where a fixture comes from
- `pytest.fake-vs-mock` — fakes for ports; `responses`/`aioresponses` at the HTTP boundary; never patch our own wrapper (python-testing 1) — J — chooses correctly for a test
- `pytest.no-parametrize` — one test function per case, deliberately — J — writes separate tests unprompted
- `pytest.test-tiers` — unit, integration, e2e in rest-api; what each catches; what CI runs — J — says which tier a test belongs in
- `pytest.break-it-on-purpose` — revert the fix, the test must go red — J — does it before stage G unprompted

QA habits to unlearn, shown side by side when they surface: verifying by looking instead of
asserting; testing through the API what a unit test says faster; re-running by hand instead
of trusting the suite; test names that narrate steps.

## ddd. Architecture

He knows the product from the outside: map the screens and API calls he has tested to the
code that serves them. `architecture-map.md` says how to build the map.

- `ddd.layers` — the repository's layers and the direction of their dependencies — P — places a file in its layer
- `ddd.request-path` — one request's path through the layers and back — P — traces a route to its response
- `ddd.schema-vs-model` — presentation schema vs domain model, and the mapping between them — J — says which one a change touches
- `ddd.repository-port` — the repository as a port in the domain, its implementation outside — J — adds a repository method in the right places
- `ddd.unit-of-work` — one transaction, explicit commit; the shared-session UoW in rest-api — J — says what is committed and when
- `ddd.command-handler` — commands, handlers, work done later through the message bus — J — traces an async job
- `ddd.repository-family` — the Central repositories and who calls whom — J — names which repository a symptom lives in

## tool. Toolchain

- `tool.gate` — the repository's gate command as a whole: run it, read red or green — P — runs the gate and reports the result
- `tool.formatters-linters` — black `--check`, ruff `--no-fix`, and why never plain `ruff check` — J — fixes a lint finding
- `tool.type-checker` — basedpyright and what a type error says — J — fixes a type error
- `tool.dependencies` — Poetry, the lock file, why a version matters — J — finds a library's version

## ci. CI and review

He has filed bugs against developers; now he answers review comments.

- `ci.pipeline` — stages and jobs, reading a red job's log — J — finds why a job failed
- `ci.mr-description` — what a reviewer needs: what, why, how tested, risk — J — drafts an MR description
- `ci.review-comments` — answering a comment: fix, or explain, never ignore — J — resolves a comment

## cc. Claude Code

He verified vendors' claims for a living: generated code is a claim.

- `cc.what-it-knows` — no runtime, no deployed values, a training cutoff; it can be wrong confidently — P — names something Claude cannot know about a ticket
- `cc.read-every-line` — every generated line is an assumption about the codebase — P — reads a hunk back with its assumptions
- `cc.prompt-pattern` — goal, files, the test, the constraints, what not to touch — J — writes a prompt that needs at most one added constraint
- `cc.failure-modes` — invented APIs, wrong assumptions, over-engineering, empty tests, scope creep, convention drift — J — catches one in review with its check
- `cc.never-commit-unexplained` — the stage G rule — P — explains every hunk of a diff
- `cc.fresh-session` — when a new session beats a long one; resuming from the ledger — J — resumes a ticket in a fresh session
- `cc.skills` — skills as checklists the session loads — J — names the skill a review applies

## eng. Engineering practice

- `eng.acceptance-criteria` — the acceptance criteria are the definition of done — P — restates them at stage A
- `eng.scope-discipline` — change what the ticket needs, nothing more; anything else is a question — J — removes or questions an out-of-scope hunk
- `eng.srp` — one job per module, class and function, and a name that says it; separation of concerns over DRY — J — splits a function doing two jobs
- `eng.ask-vs-guess` — the cost of a wrong assumption; when to ask Cristian — J — asks instead of guessing at a scope question
- `eng.small-steps` — small tasks, each ending green — J — splits a task

## Added by sessions

Concepts sessions added live in `~/.cache-mentoring/curriculum-added.md`; Cristian folds
them in here.
