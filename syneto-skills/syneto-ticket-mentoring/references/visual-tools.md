# Visual tools

Prose and a hand-drawn diagram can both be wrong, and a junior cannot tell. So the pictures
that matter come from what is really there: git-sim draws the repository's real history,
import-linter its real import graph, pyan3 its real call chain, and an artifact renders that
output, never your memory of the code. The order is always the same: he predicts first, then the picture is the answer.

The tools run through `uvx` with a pinned version, so nothing is installed into a repository
or its venv. Their output lives in `~/.cache-mentoring/visuals/`, run them from there. The
mentoring repository's `.gitignore` holds the two lines `visuals/*` and `!visuals/README.md`
(a bare `visuals/` would ignore the README too); the README's first line is the architecture
map's address (below).

## git-sim: the repository's history, live

`git-sim` 0.4.0 (GPL-2.0) reads the repository and never changes it. Its interactive pages open
by default in a viewer on initialcommit.com, so every drawing command below carries
`--open-in local`. The saved page's Share and Copy link buttons build initialcommit.com links
that carry commit subjects: he does not use them.

| Use | Command | When |
|---|---|---|
| Watch the graph change | `uvx --from git-sim==0.4.0 git-sim --open-in local --media-dir ~/.cache-mentoring/visuals live -C <checkout>` in a terminal of his own; it serves a page on `127.0.0.1` that animates every checkout, commit, reset or staged file | Levels 0–1, from the branch sequence at stage A through commit and push, while the stage's git commands run, his or yours |
| See what a command would do | `uvx --from git-sim==0.4.0 git-sim preflight -C <checkout> <git command>`: the risk, what would be lost, how to undo it, the graph; text only | The worked example for `git.never-rewrite` (preflight `reset --hard` on his branch: the commits it orphans are the lesson), and at Levels 0–1 before stage J's `branch -D` in a main-checkout run, which is the `git.squash-merge` lesson |
| One picture | `uvx --from git-sim==0.4.0 git-sim --open-in local --media-dir ~/.cache-mentoring/visuals -n 8 live --once -C <checkout>`: an SVG and an HTML page of the current graph, nothing opened | A git concept's first meeting, as the source of its artifact or handbook picture |

## import-linter: the repository's real layers

`import-linter` 2.16 (BSD-2). `drawgraph` parses the source and imports nothing; `explore`
imports the top-level package once (rest-api's `__init__.py` is empty, so nothing runs; read
another repository's before using it there). Both write `.grimp_cache/` into the current
directory, which is why they run from `~/.cache-mentoring/visuals/`, never from a repository.
The modules must be importable by name: put the repository's source root on the path (rest-api:
`PYTHONPATH=<checkout>/src`, package `central_rest_api`; elsewhere, the directory holding the
top-level package).

| Use | Command | When |
|---|---|---|
| Explore it | `PYTHONPATH=<source root> uvx --from 'import-linter[ui]==2.16' import-linter explore <package>`, in the background: it serves on `http://localhost:<port>` (the port is in its `Uvicorn running on` line) and opens a browser only when the session has a display, so give him the URL; stop it when done | `ddd.layers` and `ddd.request-path`: he clicks from the package down to the modules his ticket touches |
| The graph as data | `PYTHONPATH=<source root> uvx --from import-linter==2.16 import-linter drawgraph --show-import-totals <package or subpackage> > <name>.dot`: one arrow per dependency with its import count | `ddd.layers`'s first meeting, as the source of the architecture map (Graphviz is not installed; the artifact renders the DOT) |

The real graph rarely matches the documented layers. Show both and say which is which: rest-api's
`domain` imports `infrastructure` and `presentation`, for instance. "Which of these arrows break the rule, and why might they be there?" is a good
question for him.

## pyan3: one call chain, when he chose it

`pyan3` 2.9.0 (GPL-2.0) parses the source, imports nothing and writes nothing but its output.
It runs only on a ticket whose ledger says `call-chain: yes` (stage B). It parses with the
interpreter `uvx` runs it on, and uv's default here is 3.11: `--python` carries the
repository's own version (`<repo>/.venv/bin/python --version`; rest-api: 3.12), or every file
with newer syntax is left out.

| Use | Command | When |
|---|---|---|
| What a function calls | `uvx --python <version> --from pyan3==2.9.0 pyan3 $(find <source root>/<package> -name '*.py') --root <source root> --function <dotted name> --direction down --no-defines --annotated --text > <name>.txt` | Stage B, from the ticket's entry point (a route, a handler): he predicts the next hop, the function's block is the answer; he picks the next function and you read its block in the same file. Run again only from a new entry point, with the name as a block header gives it: the `in <namespace>` part, a dot, the name (a method is `package.module.Class.method`). A name that matches nothing gives an empty file and exit 0, not an error |

The output is everything reachable below the function, hundreds of lines for one route (1368
for rest-api's activate route on 2026-11-17): show him only the function's own block. A `[U]`
line is a name the function refers to, not only a call: a decorator's argument, a parameter's
type, a caught exception, an attribute. Keep the lines its body calls or instantiates, checked
against the body, as a table of function and the `file:line` where each is defined
(`--annotated` writes them with literal `\n` between name and place).

What it cannot see or gets wrong; say it in one line when it comes up, as a limit of the tool:

- **Calls into a library.** rest-api's routes hand work to pantheon's `async_enqueue_message`,
  and the chain stops there: the handler that does the work is found by the command's name
  (`ddd.command-handler`).
- **Calls through a list or a variable.** A validator that runs
  `for validation in self.get_validations()` reaches no validation, and `--paths-from` /
  `--paths-to` finds no path through it.
- **A method a subclass overrides.** `self.get_validations()` in `BaseValidator.run` lands on
  `BaseValidator.get_validations`, the abstract stub, not on the subclass's method that runs;
  a call through a port lands on the port. A prediction that names the subclass's method is
  correct.
- **A name it cannot place.** A library name is sometimes attached to an unrelated attribute
  of the same name: `get_current_datetime` appears to use `datetime` at
  `application/metrics/addons.py:25`, a dataclass field. Drop a line whose `file:line` does
  not hold what the body calls.
- **A file left out**, named on stderr with "leaving this file out of the analysis", means
  `--python` is older than the file's syntax: fix the version and run again.

When a hop is missing, ask him where he thinks the call goes, then open the code together: the
gap in the picture is the question.

## Artifacts: pages built from that output

Claude artifacts (the Artifact tool) are pages on Syneto's claude.ai account, private by
default; Cristian may share them. Every box, arrow and excerpt on one comes from tool output,
the repository or a test run, with its source cited on the page. An artifact is worth it when
seeing or clicking beats terminal text:

- **The architecture map**: one artifact for his whole apprenticeship, updated in place.
  Create it at `ddd.layers`'s first meeting from that repository's `drawgraph`;
  `ddd.repository-family` later adds the cross-repository edges `architecture-map.md`
  describes. Its address is the first line of `visuals/README.md`:
  `architecture map — <url> — verified <date>`. Every session looks there before creating one.
- **A structural concept's first meeting** (new → introduced) when an ASCII diagram is too
  small: for example one request's path, each step's real `file:line` excerpt behind a reveal
  (on a `call-chain: yes` ticket, built from pyan3's blocks).
  He says his prediction in the session, you grade it as any check, then he reveals.
- **A git concept's first meeting**, built from git-sim's SVG.

An artifact counts against the session caps like any explanation: it is the worked example
of a new concept, not extra material.
