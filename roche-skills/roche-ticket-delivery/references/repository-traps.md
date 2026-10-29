# Repository traps

What a brief for each repository must carry. Facts as of 2026-10-16. When a line disagrees
with the repository, the repository wins: fix this file in the same session.

`<repo>` is the main checkout. Every gate runs from the tree under test.

**Docker** runs in Colima: an aarch64 VM with 4 CPUs and 8 GiB, which mounts only `$HOME`.
A bind mount from the session scratchpad (`/private/tmp/...`) comes up empty in the
container, so every tree a container sees lives under `$HOME`. A
`<repo>/.claude/worktrees/<name>` worktree qualifies. Every Docker run happens in the
orchestrator's Docker session (SKILL.md, *Working rules*): one session at a time under
`~/.cache/docker-tests.lock`, with no `rdnx-*` container left at the end except the ones
`ledger.md` says he keeps. A subagent's brief carries the subagent Docker lines instead. Never install or reconfigure Docker or Colima yourself.

## rdnx — `remix/nifs/rdnx`

- **What it is:** the package-management service for REC. It is a Rust workspace (`app/`,
  `core/`, `crates/`, `libdnf5-adapter/`) that drives libdnf5 in process and serves a gRPC
  API (`package_management.v1`) over a Unix domain socket. Its layout is set out in
  `docs/layout.md`, its structure rules in `docs/testing.md` (*Structure rules*), and its
  design in `docs/architecture.md` and RFD-001. rdnx has a `CLAUDE.md` (with
  `.claude/rules/rust.md` and `.claude/rules/workflow.md`) but no `project_structure.md`, so
  every Rust agent reads `docs/layout.md` as its `project_structure.md`. Say so in every
  brief.
- **Agents:** `rust-implementor-expert-no-commit`, `rust-fixer-no-commit`,
  `rust-test-writer`, `rust-issue-investigator`, `rust-code-reviewer`,
  `rust-structure-and-style-guard` and, at stage 8, `rust-code-designer` for naming. Workers load **rust-code-style**, **rust-testing**,
  **rust-project-structure** and **rust-design-idioms**.
- **Platform:** the target is `rockylinux:10.2` on x86_64. The vendored libdnf5 stack
  (`vendor/libdnf5-5.4.5.0/`) is x86_64 RPMs, and the local `rdnx-*` images are `amd64`.
  Every `docker build` and `docker run` needs `DOCKER_DEFAULT_PLATFORM=linux/amd64` in its
  environment. Prefix the command with it, because the shell does not set it. Everything
  runs under emulation: a cold image build takes on the order of a quarter of an hour, and
  a warm one takes seconds.
- **Gate**, from the root of the tree under test:
  `DOCKER_DEFAULT_PLATFORM=linux/amd64 just quality-gate`. It builds `rdnx-builder:dev`,
  then runs `cargo fmt --all --check`, `cargo clippy --workspace --all-targets --locked -- -D warnings`,
  `cargo test --workspace --locked` and `cargo audit --deny unsound` in it. It is
  non-mutating, so a read-only final gate can run it. The host has rustup, cargo and just,
  but no libdnf5, which exists only in the image: never run `cargo` on the Mac directly.
- **Gate prerequisite:** the adapter's integration tests, part of `cargo test --workspace`,
  open real libdnf5 sessions against `libdnf5-adapter/tests/fixtures/generated/`, which is
  git-ignored, and panic without it (`docs/testing.md`, *Gates in the builder*). In a tree
  without that directory, run `DOCKER_DEFAULT_PLATFORM=linux/amd64 just test-adapter-fixtures`
  first, under the lock.
- **Focused commands (writers and investigators):** the Rust agents iterate with
  `cargo check`, `cargo clippy` and focused `cargo test -p <crate> [--test <target>] [<filter>]`.
  Run them in the builder image, from the root of the tree under test, under the lock:
  `DOCKER_DEFAULT_PLATFORM=linux/amd64 docker run --rm -v "$PWD":/src -v rdnx-cargo-registry:/root/.cargo/registry -v <target volume>:/src/target -w /src rdnx-builder:dev cargo <subcommand> --locked <args>`.
  `rdnx-builder:dev` must exist, so run the gate once first. The full gate still runs once
  before the worker reports.
- **Formatter (writers only):** the same `docker run` line ending in `cargo fmt --all`,
  without `--locked`, which `cargo fmt` rejects.
- **Target volume:** `<target volume>` is `rdnx-target` in the main worktree,
  `rdnx-target-<KEY>` in the separate worktree, and `rdnx-target-<KEY>-<name>` in a
  temporary `--detach` worktree.
- **Linked worktree:** the recipe mounts the `rdnx-target` volume, which the main checkout
  shares. In a linked worktree, first run
  `DOCKER_DEFAULT_PLATFORM=linux/amd64 just builder-image-build` from `<worktree>` (a
  private recipe, callable by name; it is the gate's own dependency), then the recipe's
  `docker run` line by hand, from `<worktree>`, with `-v rdnx-target-<KEY>:/src/target` in
  place of `-v rdnx-target:/src/target`. Each tree then has its own build cache; stage 11
  removes the volume. `rdnx-builder:dev` is one tag for every tree: when the change edits
  `docker/Dockerfile.builder` or `rust-toolchain.toml`, the build rebuilds the shared tag,
  so say so in the report.
- **Docker suites** (`tests/*/README.md`), outside the gate, each prefixed with
  `DOCKER_DEFAULT_PLATFORM=linux/amd64`: `just test-smoke-all`, `just test-system-all`,
  `just test-reclike-all`, and `just test-parity scenario=all`. The smoke suite leaves
  `rdnx-repo` running and the system suite leaves `rdnx-systest-repo`: the orchestrator
  removes them when it ends the Docker session. When `ledger.md` keeps `rdnx-repo`, run the
  smoke suite with `RDNX_REPO=rdnx-repo-<key in lower case>` in its environment
  (`fixtures/docker-helpers.sh` supports it): it then leaves his container alone. Each
  case takes seconds to minutes. They use fixed container names (`rdnx-systest-*`,
  `rdnx-reclike-*`, `rdnx-fixbuild*`, `rdnx-svc-*`) and named volumes (`rdnx-seed`,
  `rdnx-systest-readonly-identity`), so they run one at a time, under the lock. The plan
  names the suites a change needs. Transcripts go to `evidence/`, which is git-ignored. The
  generated repositories (`fixtures/repo*`, `tests/system/repo/`, `tests/reclike/repo/`,
  `libdnf5-adapter/tests/fixtures/generated/`) are git-ignored too, and the `*-fixtures`
  recipes rebuild them. A case that cannot run here goes into the stage 8 report as not
  run, never as passed.
- **CI:** none yet: there is no `.gitlab-ci.yml`, and NIFS-13632 tracks the pipeline. Until
  it lands, the local gate is the only check, and stage 8 must say it ran.
- **Traps:** `docs/agents/` and `docs/handoffs/` are git-ignored orchestration artefacts:
  nothing a ticket delivers goes there. The README and `docs/` describe the service, so
  every change to behaviour or to the socket API is a docs change too.
- **Docs**, for stage 8's writer and every reviewer:
  - RFDs (`docs/rfds/`) and ADRs (`docs/adrs/`) carry product content only: requirements,
    risks, recommendations, decisions and acceptance criteria. Never PoC notes, commit
    hashes, "fixed in the PoC", or what the code currently implements.
  - Argue a design choice on technical grounds only. Never write business or staffing
    context into a technical doc, such as why Rust was chosen as a matter of company
    policy.
  - `docs/gaps/` is a register. A code gap found during a ticket that is out of the locked
    scope gets an entry there and nothing else: "Registered only; it will be solved later
    as a ticket." Never fix it in this ticket, never offer to. Do not cite gap entries as
    arguments in a design defence.
