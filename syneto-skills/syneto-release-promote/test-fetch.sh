#!/usr/bin/env bash
# Local-only regression: --check must refresh release refs in a narrow clone.
set -euo pipefail

skill_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
fixture_root=$(mktemp -d)
trap 'rm -rf -- "$fixture_root"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME='Fetch test' GIT_AUTHOR_EMAIL='fetch-test@example.invalid'
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
unset SYNETO_SKIP_FETCH SYNETO_INCLUDE_CENTRAL SYNETO_ALLOW_MINORITY_PAIR
unset SYNETO_PROMOTE_CONFIRM

git init --quiet --initial-branch=main "$fixture_root/origin"
git -C "$fixture_root/origin" commit --quiet --allow-empty -m 'Initial commit'
git -C "$fixture_root/origin" branch central-2.9
git -C "$fixture_root/origin" branch central-2.10
mkdir "$fixture_root/projects"
git clone --quiet "$fixture_root/origin" "$fixture_root/projects/product"
checkout="$fixture_root/projects/product"
git -C "$checkout" branch central-2.10 origin/central-2.10 >/dev/null
git -C "$checkout" config remote.origin.fetch '+refs/heads/main:refs/remotes/origin/main'
original_dev=$(git -C "$checkout" rev-parse central-2.10)
original_prod=$(git -C "$checkout" rev-parse origin/central-2.9)

git -C "$fixture_root/origin" switch --quiet central-2.10
git -C "$fixture_root/origin" commit --quiet --allow-empty -m 'CENTRAL-123 New release work'
latest_dev=$(git -C "$fixture_root/origin" rev-parse HEAD)

# Reproduce the old failure: default fetch succeeds but leaves dev stale.
git -C "$checkout" fetch --quiet --prune origin
test "$(git -C "$checkout" rev-parse origin/central-2.10)" = "$original_dev"

export SYNETO_PROJECTS_ROOT="$fixture_root/projects"
export SYNETO_PROMOTE_PAIR='central-2.9 central-2.10'
bash "$skill_directory/promote.sh" --check >"$fixture_root/check.log" 2>&1 || {
    cat "$fixture_root/check.log"
    exit 1
}
test "$(git -C "$checkout" rev-parse origin/central-2.10)" = "$latest_dev"
test "$(git -C "$checkout" rev-parse central-2.10)" = "$original_dev"
test "$(git -C "$checkout" rev-parse origin/central-2.9)" = "$original_prod"
test "$(git -C "$checkout" branch --show-current)" = main
test -z "$(git -C "$checkout" status --porcelain)"
grep -q 'CENTRAL-123' "$fixture_root/check.log"
grep -q 'Preflight clean' "$fixture_root/check.log"

# A deleted remote dev branch must be pruned, never reused from stale refs.
git -C "$fixture_root/origin" switch --quiet main
git -C "$fixture_root/origin" branch -D central-2.10 >/dev/null
if bash "$skill_directory/promote.sh" --check product >"$fixture_root/deleted.log" 2>&1; then
    echo 'FAIL: accepted a deleted remote dev branch' >&2
    exit 1
fi
if git -C "$checkout" show-ref --verify --quiet refs/remotes/origin/central-2.10; then
    echo 'FAIL: stale remote dev ref survived pruning' >&2
    exit 1
fi
echo 'PASS: narrow-clone refresh, unchanged local dev, and deleted-branch refusal'
