# Visual tools

Prose and a hand-drawn diagram can both be wrong, and a junior cannot tell. So the pictures
that matter come from what is really there: git-sim draws the repository's real history,
import-linter its real import graph, and an artifact renders that output, never your memory
of the code. The order is always the same: he predicts first, then the picture is the answer.

Both tools run through `uvx` with a pinned version, so nothing is installed into a repository
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
  small: for example one request's path, each step's real `file:line` excerpt behind a reveal.
  He says his prediction in the session, you grade it as any check, then he reveals.
- **A git concept's first meeting**, built from git-sim's SVG.

An artifact counts against the session caps like any explanation: it is the worked example
of a new concept, not extra material.
