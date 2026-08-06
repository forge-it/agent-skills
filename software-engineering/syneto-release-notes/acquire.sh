#!/usr/bin/env bash
#
# Acquire the commit corpus for a Syneto release-notes entry.
#
# Read-only with respect to every worktree. This script fetches remote-tracking
# refs and reads logs. It never checks out, stashes, resets, merges, or writes
# to any repository. A dirty worktree is reported, never touched.
#
# Usage:
#   ./acquire.sh                            # derive the branch pair
#   ./acquire.sh central-2.9 central-2.10   # explicit <prod> <dev> override
#
# Exit codes:
#   0  success
#   1  fatal — do not publish; read stderr. Causes include: bad argument count,
#      unusable checkout root, no central-<N>.<N> refs found, fewer than two
#      versions to form a pair, mktemp failure, an empty release range, and a
#      pair that fails the quorum guard.
#
# Environment:
#   SYNETO_PROJECTS_ROOT         defaults to /home/cristi/Projects
#   SYNETO_SKIP_FETCH            set to 1 to reuse local refs (offline / dry runs)
#   SYNETO_ALLOW_MINORITY_PAIR   set to 1 to downgrade the quorum guard to a
#                                warning, for a deliberate minority release

set -uo pipefail

projects_root="${SYNETO_PROJECTS_ROOT:-/home/cristi/Projects}"
infrastructure_repository="central"
infrastructure_prod_ref="production-on-prem"
infrastructure_dev_ref="dev-on-prem"
fetch_concurrency=12

# Repositories that still carry central-<N>.<N> refs but have left the release
# train. Excluded from discovery and REPORTED — never silently dropped, because
# a wrongly-excluded repository is invisible in the finished release notes.
#
# Kept in sync BY HAND with the identical list in
# ../syneto-release-promote/promote.sh. The two skills must agree on what is out
# of the release; if you change one, change the other in the same commit.
retired_repositories=("central-vat-searcher")

is_retired() {
    local needle="$1" entry
    for entry in "${retired_repositories[@]}"; do
        [ "$entry" = "$needle" ] && return 0
    done
    return 1
}

if [ "$#" -ne 0 ] && [ "$#" -ne 2 ]; then
    echo "FATAL: expected no arguments (derive the pair) or exactly two (<prod> <dev>); got $#." >&2
    exit 1
fi

cd "$projects_root" || { echo "FATAL: cannot enter $projects_root" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Candidate repositories: anything holding at least one exact central-<N>.<N>
# remote ref, plus the infrastructure repository. The exact pattern is what
# keeps decoys such as origin/central-2.9-backup out of the pair derivation.
# ---------------------------------------------------------------------------
release_pattern='^origin/central-[0-9]+\.[0-9]+$'
candidate_repositories=()
excluded_repositories=()

for candidate in */; do
    repository="${candidate%/}"
    # -e not -d: a linked worktree or submodule has .git as a file.
    [ -e "$repository/.git" ] || continue
    if [ "$repository" = "$infrastructure_repository" ]; then
        candidate_repositories+=("$repository")
        continue
    fi
    if git -C "$repository" for-each-ref --format='%(refname:short)' refs/remotes/origin/ 2>/dev/null \
        | grep -qE "$release_pattern"; then
        if is_retired "$repository"; then
            excluded_repositories+=("$repository")
        else
            candidate_repositories+=("$repository")
        fi
    fi
done

if [ "${#candidate_repositories[@]}" -eq 0 ]; then
    echo "FATAL: no repositories with central-<N>.<N> refs under $projects_root" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Fetch. Stale remote-tracking refs are the single largest source of silently
# wrong release notes, so a fetch failure is reported WITH its reason — an auth
# failure and a missing remote need different responses from the operator.
# --prune only removes remote-tracking refs; it never touches local branches
# or the worktree.
# ---------------------------------------------------------------------------
fetch_failure_log="$(mktemp)" || { echo "FATAL: cannot create temp file" >&2; exit 1; }
trap 'rm -f "$fetch_failure_log"' EXIT

if [ "${SYNETO_SKIP_FETCH:-0}" != "1" ]; then
    running=0
    for repository in "${candidate_repositories[@]}"; do
        {
            fetch_error=$(git -C "$repository" fetch --quiet --prune origin 2>&1) \
                || printf '%s\t%s\n' "$repository" "${fetch_error//[$'\n\t']/ }" \
                    >>"$fetch_failure_log"
        } &
        running=$((running + 1))
        if [ "$running" -ge "$fetch_concurrency" ]; then wait; running=0; fi
    done
    wait
fi
mapfile -t fetch_failures <"$fetch_failure_log"

# ---------------------------------------------------------------------------
# Branch pair. Version-sorted NUMERICALLY: central-2.9 sorts ABOVE central-2.10
# lexically, so a plain sort picks the wrong pair. Highest = dev, next = prod.
# ---------------------------------------------------------------------------
if [ "$#" -eq 2 ]; then
    prod_branch="$1"
    dev_branch="$2"
    pair_origin="operator-supplied"
else
    mapfile -t sorted_versions < <(
        for repository in "${candidate_repositories[@]}"; do
            git -C "$repository" for-each-ref --format='%(refname:short)' refs/remotes/origin/ 2>/dev/null \
                | grep -E "$release_pattern" | sed 's|^origin/central-||'
        done | sort -u -t. -k1,1n -k2,2n
    )
    version_count="${#sorted_versions[@]}"
    if [ "$version_count" -lt 2 ]; then
        echo "FATAL: need two central-<N>.<N> versions to form a pair; found $version_count" >&2
        exit 1
    fi
    dev_branch="central-${sorted_versions[$((version_count - 1))]}"
    prod_branch="central-${sorted_versions[$((version_count - 2))]}"
    pair_origin="derived-by-numeric-version-sort"
fi

# ---------------------------------------------------------------------------
# Per-repository ranges.
#   TICKETS  -> ids in commit SUBJECTS, including merge subjects. GitLab merge
#               subjects carry the ticket id for merged work while direct pushes
#               carry it in their own subject.
#   XREF     -> ids appearing ONLY in commit bodies. These are usually
#               cross-references to OTHER tickets that are not shipping ("parity
#               with SYN-2346"). NOT release content. Deliberately NOT named
#               TICKETS-something: a `grep '^TICKETS'` must not match this
#               bucket, or the ids it exists to quarantine flow straight back in.
#   COMMIT   -> --no-merges subjects, the material for descriptions.
# Only SYN- (Jira) and CENTRAL- (legacy YouTrack) are ticket ids.
# ---------------------------------------------------------------------------
ticket_pattern='\b(SYN|CENTRAL)-[0-9]+'

emit_repository_range() {
    local repository="$1" prod_ref="$2" dev_ref="$3" tag="$4"

    git -C "$repository" rev-parse --verify --quiet "$prod_ref" >/dev/null || return 1
    git -C "$repository" rev-parse --verify --quiet "$dev_ref" >/dev/null || return 1

    local range="$prod_ref..$dev_ref"
    local total merges tip subject_tickets body_tickets crossref_tickets

    total=$(git -C "$repository" rev-list --count "$range" 2>/dev/null) || return 3
    [ -z "$total" ] && return 3
    [ "$total" -eq 0 ] && return 2

    merges=$(git -C "$repository" rev-list --count --merges "$range" 2>/dev/null)
    tip=$(git -C "$repository" log -1 --format=%cd --date=short "$dev_ref" 2>/dev/null)

    subject_tickets=$(git -C "$repository" log --format='%s' "$range" 2>/dev/null \
        | grep -oE "$ticket_pattern" | sort -u)
    body_tickets=$(git -C "$repository" log --format='%b' "$range" 2>/dev/null \
        | grep -oE "$ticket_pattern" | sort -u)
    # LC_ALL=C keeps both sides of comm on one byte-ordered collation; a locale
    # that ignores the hyphen could otherwise desynchronise the two sorts.
    crossref_tickets=$(LC_ALL=C comm -13 \
        <(printf '%s\n' "$subject_tickets" | LC_ALL=C sort -u) \
        <(printf '%s\n' "$body_tickets" | LC_ALL=C sort -u) | grep -v '^$')

    printf 'REPO\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$repository" "$tag" "$range" "$total" "$merges" "$tip"
    printf 'TICKETS\t%s\t%s\n' "$repository" "$(echo "$subject_tickets" | tr '\n' ' ')"
    printf 'XREF\t%s\t%s\n' "$repository" "$(echo "$crossref_tickets" | tr '\n' ' ')"

    git -C "$repository" log --no-merges --format="COMMIT%x09$repository%x09%h%x09%s" "$range" 2>/dev/null
    return 0
}

echo "=== RELEASE PAIR ==="
printf 'prod\t%s\ndev\t%s\nsource\t%s\ninfra\t%s..%s\n' \
    "$prod_branch" "$dev_branch" "$pair_origin" \
    "$infrastructure_prod_ref" "$infrastructure_dev_ref"

echo
echo "=== CONTRIBUTING REPOSITORIES ==="
echo "# REPO<tab>name<tab>tag<tab>range<tab>commits<tab>merges<tab>tip-date"
echo "# TICKETS<tab>name<tab>space-separated ids from commit subjects"
echo "# XREF<tab>name<tab>body-only ids — cross-references to other tickets, not release content"
echo "# COMMIT<tab>name<tab>sha<tab>subject"
contributing_repositories=()
empty_repositories=()
unresolved_repositories=()
failed_repositories=()
pair_resolved_count=0

for repository in "${candidate_repositories[@]}"; do
    is_infrastructure=0
    if [ "$repository" = "$infrastructure_repository" ]; then
        is_infrastructure=1
        emit_repository_range "$repository" \
            "origin/$infrastructure_prod_ref" "origin/$infrastructure_dev_ref" "platform"
    else
        emit_repository_range "$repository" \
            "origin/$prod_branch" "origin/$dev_branch" "product"
    fi
    outcome=$?
    case "$outcome" in
        0) contributing_repositories+=("$repository") ;;
        1) unresolved_repositories+=("$repository") ;;
        2) empty_repositories+=("$repository") ;;
        3) failed_repositories+=("$repository") ;;
    esac
    # Quorum arithmetic counts only repositories that actually use the release
    # pair. `central` runs on its own fixed refs, so it is evidence of nothing
    # about whether the pair is right — and it always contributes, which would
    # otherwise put a permanent floor of 1 under the guard.
    if [ "$is_infrastructure" -eq 0 ] && { [ "$outcome" -eq 0 ] || [ "$outcome" -eq 2 ]; }; then
        pair_resolved_count=$((pair_resolved_count + 1))
    fi
done

echo
echo "=== EMPTY RANGES (pair resolves, no commits — correctly omitted) ==="
printf '%s\n' "${empty_repositories[@]:-none}"

# A candidate that cannot resolve the current pair is either genuinely retired
# (its newest release branch predates this pair) or a clone whose fetch failed.
# Never drop it silently — the difference is invisible from ref state alone.
echo
echo "=== PAIR DOES NOT RESOLVE (verify these are retired, not stale clones) ==="
printf '%s\n' "${unresolved_repositories[@]:-none}"

echo
echo "=== RANGE READ FAILED (git error — treat as unknown, not as empty) ==="
printf '%s\n' "${failed_repositories[@]:-none}"

echo
echo "=== EXCLUDED AS RETIRED (operator-configured, not scanned) ==="
printf '%s\n' "${excluded_repositories[@]:-none}"

# ---------------------------------------------------------------------------
# Operator flags. Dirty worktrees are surfaced and left exactly as they are.
# ---------------------------------------------------------------------------
echo
echo "=== DIRTY WORKTREES (left untouched — operator must review) ==="
dirty_found=0
for repository in "${candidate_repositories[@]}"; do
    dirty_entries=$(git -C "$repository" status --porcelain 2>/dev/null | wc -l)
    [ "$dirty_entries" -eq 0 ] && continue
    status="not-contributing"
    for contributor in "${contributing_repositories[@]}"; do
        [ "$contributor" = "$repository" ] && status="CONTRIBUTING" && break
    done
    printf '%s\t%s uncommitted entries\t%s\n' "$repository" "$dirty_entries" "$status"
    dirty_found=1
done
[ "$dirty_found" -eq 0 ] && echo "none"

echo
echo "=== FETCH FAILURES (ranges above may be stale) ==="
printf '%s\n' "${fetch_failures[@]:-none}"

echo
echo "=== SUMMARY ==="
printf 'contributing_repositories\t%s\n' "${#contributing_repositories[@]}"
printf 'candidate_repositories\t%s\n' "${#candidate_repositories[@]}"
printf 'product_repos_resolving_pair\t%s\n' "$pair_resolved_count"

if [ "${#contributing_repositories[@]}" -eq 0 ]; then
    echo "FATAL: no repository has commits in $prod_branch..$dev_branch." >&2
    echo "Either the release is already merged, or the pair is wrong." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Quorum guard. At a major-release rollover the first team to cut central-2.11
# would otherwise flip the derived pair for the entire fleet: one repository
# resolves the new pair, every other repository fails it, and the run publishes
# a one-repository release.
#
# The denominator is every product repository where the pair RESOLVES, with or
# without commits. A repository that has cut the new branch but pushed nothing
# yet agrees with the derivation, so counting only non-empty ranges would abort
# the first run of every new cycle for no reason.
#
# This fires for a supplied pair as well as a derived one. An autonomous run has
# no operator to read a warning, and demoting the supplied case to a warning
# would let the derived case's own remediation advice route around the guard.
# ---------------------------------------------------------------------------
if [ "${#unresolved_repositories[@]}" -gt "$pair_resolved_count" ]; then
    message="$pair_origin pair $prod_branch..$dev_branch resolves in $pair_resolved_count product repositories but fails in ${#unresolved_repositories[@]}"
    if [ "${SYNETO_ALLOW_MINORITY_PAIR:-0}" = "1" ]; then
        echo "WARNING: $message — proceeding under SYNETO_ALLOW_MINORITY_PAIR=1." >&2
    else
        echo "FATAL: $message." >&2
        echo "Either a newly-cut release branch flipped the derivation, or the supplied pair is wrong." >&2
        echo "Re-run with the correct pair, or set SYNETO_ALLOW_MINORITY_PAIR=1 if a minority release is intended." >&2
        exit 1
    fi
fi
