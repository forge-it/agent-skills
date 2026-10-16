# Repository facts

One entry per Roche repository the review has met: its stack (a row of SKILL.md's stack
table), its gate, its structure document, and the facts every lens gets. Facts as of
2026-10-16. When a line disagrees with the repository, the repository wins: fix this file in
the same session. For a repository with no entry, read its CLAUDE.md, README, justfile and
layout, propose an entry to him, and add it once he agrees.

## Docker rule

Docker on this Mac runs in Colima, an aarch64 VM that mounts only `$HOME`; the run directory
is under `$HOME`, so the worktree mounts. Docker runs one session at a time on this machine,
under a lock shared with every other skill:

1. **Take the lock:** `mkdir ~/.cache/docker-tests.lock`, then
   `echo "mr-review <repo>-<iid> pid=$PPID $(date -Iseconds)" > ~/.cache/docker-tests.lock/owner`.
   When `mkdir` fails, read `owner`, tell him who holds it, and wait in a background Bash
   (`until [ ! -d ~/.cache/docker-tests.lock ]; do sleep 30; done`). Never remove a lock you
   did not take: ask him.
2. **Note what is already there:** `docker ps -a --format '{{.Names}}'` before the gate. Those
   containers are not yours: leave them.
3. **Run the gate in the background** (`run_in_background`) and wait for its exit.
4. **End the session in the same turn, pass, fail or killed:** remove only the containers the
   gate started (the ones not in step 2's list), check that
   `docker ps -q --filter volume=<this run's build volume>` lists nothing, then
   `rm -r ~/.cache/docker-tests.lock`.

## rdnx — `remix/nifs/rdnx`

- **Stack:** Rust. A workspace (`app/`, `core/`, `crates/`, `libdnf5-adapter/`) that drives
  libdnf5 in process and serves a gRPC API (`package_management.v1`) over a Unix socket.
- **Structure document:** `docs/layout.md`. rdnx has no `CLAUDE.md` or
  `project_structure.md`. The rules the gate enforces are in `docs/testing.md`
  (*Structure rules*).
- **Gate**, from `<run>/wt`, under the Docker rule:
  1. `DOCKER_DEFAULT_PLATFORM=linux/amd64 just test-adapter-fixtures`, on every gate, a
     rerun after a push included: the adapter's integration tests read the git-ignored
     `libdnf5-adapter/tests/fixtures/generated/`, which a fresh worktree lacks and a rerun
     holds from the previous head.
  2. `DOCKER_DEFAULT_PLATFORM=linux/amd64 just builder-image-build`. `rdnx-builder:dev` is
     one tag for every checkout on this machine. When the MR edits `docker/Dockerfile.builder`
     or `rust-toolchain.toml`, this step rebuilds the shared tag from the MR's files: say so
     in `gate.md`, and tell him at close.
  3. Every check of the `quality-gate` recipe, each one run whatever the one before did:
     ```
     DOCKER_DEFAULT_PLATFORM=linux/amd64 docker run --rm -v "$PWD":/src -v rdnx-cargo-registry:/root/.cargo/registry -v rdnx-target-mr-<iid>:/src/target -w /src rdnx-builder:dev bash -c 'status=0; for step in "fmt --all --check" "clippy --workspace --all-targets --locked -- -D warnings" "test --workspace --locked --no-fail-fast" "audit --deny unsound"; do echo "== cargo $step"; cargo $step || { echo "== FAILED: cargo $step"; status=1; }; done; exit $status'
     ```
     The recipe chains its checks with `&&`, so one unformatted line would hide clippy, the
     tests and audit; `--no-fail-fast` runs every test binary. The target volume
     `rdnx-target-mr-<iid>` is the review's own, so it never shares the main checkout's
     build cache. Never copy the recipe line itself: bash leaves its
     `{{justfile_directory()}}` unexpanded, and Docker rejects it.
  The vendored libdnf5 RPMs are x86_64, so every Docker command needs
  `DOCKER_DEFAULT_PLATFORM=linux/amd64`. A cold run under emulation takes about a quarter of
  an hour. At close, also `docker volume rm rdnx-target-mr-<iid>`. The Docker suites
  (`just test-smoke-all` and the others) are not part of the review's gate.
- **Facts for every lens:**
  - The gRPC proto `package_management.v1` is the public contract with REC: a removed or
    renumbered field, or a changed RPC, is a contract break.
  - The service drives libdnf5 through an FFI adapter (`libdnf5-adapter/`) and runs with
    elevated rights: `unsafe` is allowed only where the structure rules in `docs/testing.md`
    grant it, and package and repository signature checks must not be weakened.
  - RFDs (`docs/rfds/`) and ADRs (`docs/adrs/`) carry product content only: requirements,
    risks, decisions and acceptance criteria, never PoC notes or what the code currently
    implements. A design choice is argued on technical grounds only; business context never
    goes into a technical doc. `docs/gaps/` is a register: an out-of-scope gap gets an entry
    there, not a fix.
  - `docs/rfds/0001-*.md` is about 400 KB: search it for the symbols in play, never read it
    whole.
