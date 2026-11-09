# Building the architecture map

The junior learns the architecture one ticket slice at a time (`ddd.layers`,
`ddd.request-path`, `ddd.repository-family`). This file says where the facts come from and how
the map grows; it holds no architecture of its own, because a map copied here would go stale
and he would learn it wrong.

## Sources, in order of trust

1. **The code**, at the line you quote, and import-linter's count of its imports
   (`visual-tools.md`).
2. **The repository's `CLAUDE.md`, `AGENTS.md` and `docs/decisions/`**: rest-api's `CLAUDE.md`
   names its layer packages (`api`, `application`, `domain`, `adapters`, `infrastructure`,
   `presentation`), the unit of work to use, and the ADRs to read before touching an area.
3. **The repository's section of the senior's `references/repository-traps.md`**: stack, gate,
   the tiers and what each needs.
4. Your own knowledge of the frameworks (FastAPI, SQLAlchemy, pytest), checked against the
   versions in `poetry.lock`.

When two disagree, the higher one wins, and you say so. The docs describe the intended
layers and the import graph the real ones: when those differ, he hears both and which is
which.

## How it grows

- **Stage B of every ticket**: draw only this ticket's slice, from the route or entry point to
  the store and back, every box a real module with its `file:line`. Mark the part the ticket
  changes with `▲`.
- **A layer's first appearance** (new → introduced): its handbook page holds the full layer
  diagram of that repository, with the dependency direction and one sentence per layer.
- **`ddd.repository-family`**, when a ticket crosses a repository boundary, or a symptom lives
  in another repository: draw the Central repositories involved and who calls whom, only the
  edges you verified (an HTTP client, a queue name, a gRPC stub, each with `file:line`). Add them to
  the architecture map artifact, at the address `visual-tools.md` gives: each edge with its
  source line, and the "verified <date>" updated.
- **When a session finds the map wrong**: fix the page, say "the map was wrong" at the top of
  the next explanation, and redraw.

## What to connect it to

He tested the product from the outside: for each slice, name the screen or API call he would
have tested that runs through it. That turns his QA knowledge into the map's entry points.
