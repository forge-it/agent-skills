#!/usr/bin/env bash
#
# Acquire the commit corpus for a SCOPED Syneto release-notes entry: only the
# repositories named on the command line become release content. The fleet is
# still fetched and classified — the branch pair, the quorum guard, and the
# OUTSIDE bucket (out-of-scope subject tickets) are all fleet-wide — but
# REPO/TICKETS/XREF/COMMIT records are emitted for the selected repositories
# alone.
#
# Read-only with respect to every worktree. This script fetches remote-tracking
# refs and reads logs. It never checks out, stashes, resets, merges, or writes
# to any repository. A dirty worktree is reported, never touched.
#
# Usage:
#   ./acquire.sh <repository> [<repository>...]
#   SYNETO_NOTES_PAIR="central-2.9 central-2.10" ./acquire.sh <repository>...
#
# At least one repository name is REQUIRED. This script never falls back to
# scanning the whole fleet — a whole-fleet entry is the parent skill's
# acquire.sh (../syneto-release-notes/acquire.sh), not this one.
#
# Exit codes:
#   0  success — every selected repository is contributing (or, under
#      SYNETO_ALLOW_EMPTY_SELECTION=1, empty, with at least one contributing)
#   1  fatal — do not publish; read stderr. Causes include: no repository
#      named; an unknown flag; a name with a path separator; a name that is
#      not a git checkout under the projects root; constants drifted from the
#      parent acquire.sh; a malformed or reversed SYNETO_NOTES_PAIR; a fetch
#      failure in a selected repository; a selected repository whose pair does
#      not resolve; a selected repository whose range read failed; an empty
#      range in any selected repository (override with
#      SYNETO_ALLOW_EMPTY_SELECTION=1); every selected range empty (never
#      overridable); a quorum-guard failure; an unusable checkout root; a
#      mktemp failure.
#
# Environment:
#   SYNETO_PROJECTS_ROOT           defaults to /home/cristi/Projects
#   SYNETO_SKIP_FETCH              1 reuses local refs (offline / dry runs)
#   SYNETO_NOTES_PAIR              "<prod> <dev>" explicit pair, validated for
#                                  shape AND ordering — reversed, every range
#                                  reads backwards and the run dies blaming
#                                  the ranges instead of the pair
#   SYNETO_ALLOW_MINORITY_PAIR     1 downgrades the quorum guard to a warning
#   SYNETO_ALLOW_EMPTY_SELECTION   1 tolerates SOME selected repositories
#                                  having empty ranges; ALL empty stays fatal
#
# TWO PASSES — DO NOT COLLAPSE THEM. Pass 1 classifies every fleet candidate;
# that is what keeps the pair derivation, the quorum guard, and the OUTSIDE
# bucket fleet-wide. Pass 2 emits records for the selected repositories only.
# Filtering pass 1 by selection silently turns the quorum guard into a no-op,
# because its counters are fed by that loop.

set -uo pipefail

projects_root="${SYNETO_PROJECTS_ROOT:-/home/cristi/Projects}"
infrastructure_repository="central"
infrastructure_prod_ref="production-on-prem"
infrastructure_dev_ref="dev-on-prem"
fetch_concurrency=12

# Repositories that still carry central-<N>.<N> refs but have left the release
# train. Excluded from discovery and REPORTED — never silently dropped. Naming
# a retired repository explicitly overrides the exclusion with a warning,
# matching promote.sh: the list governs discovery, and an operator's explicit
# name is not discovery.
#
# Kept in sync BY HAND with the identical lists in
# ../syneto-release-notes/acquire.sh and ../syneto-release-promote/promote.sh.
# The startup assertion below turns silent drift from the parent acquire.sh
# into a fatal error; promote.sh is still checked by hand.
retired_repositories=("central-vat-searcher")

release_pattern='^origin/central-[0-9]+\.[0-9]+$'
ticket_pattern='\b(SYN|CENTRAL)-[0-9]+'
# Bare branch names (no origin/ prefix), for SYNETO_NOTES_PAIR validation only.
pair_branch_pattern='^central-[0-9]+\.[0-9]+$'

# ---------------------------------------------------------------------------
# Constants-drift assertion. This script is a deliberate copy of the parent
# acquire.sh (separation of concerns over DRY); the price of the copy is that
# shared constants can drift apart silently. Make drift loud instead: compare
# the exact assignment lines and refuse to run on any mismatch.
# ---------------------------------------------------------------------------
self_script="$(readlink -f "${BASH_SOURCE[0]}")"
parent_acquire_script="$(dirname "$self_script")/../syneto-release-notes/acquire.sh"

assert_constant_in_sync() {
    local anchor="$1" ours theirs
    ours=$(grep -m1 -E "$anchor" "$self_script") || {
        echo "FATAL: constant matching $anchor is missing from this script." >&2
        exit 1
    }
    theirs=$(grep -m1 -E "$anchor" "$parent_acquire_script" 2>/dev/null) || {
        echo "FATAL: cannot read the constant matching $anchor from the parent script at" >&2
        echo "  $parent_acquire_script" >&2
        echo "Either the parent moved, or the constant was renamed there — re-sync the scripts." >&2
        exit 1
    }
    if [ "$ours" != "$theirs" ]; then
        echo "FATAL: a shared constant drifted between this script and the parent acquire.sh:" >&2
        echo "  parent: $theirs" >&2
        echo "  scoped: $ours" >&2
        echo "Re-sync the two scripts in the same commit, then re-run." >&2
        exit 1
    fi
}

for constant_anchor in \
    '^retired_repositories=' \
    '^release_pattern=' \
    '^ticket_pattern=' \
    '^infrastructure_repository=' \
    '^infrastructure_prod_ref=' \
    '^infrastructure_dev_ref='; do
    assert_constant_in_sync "$constant_anchor"
done

usage() {
    sed -n '3,51p' "$self_script" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

is_retired() {
    local needle="$1" entry
    for entry in "${retired_repositories[@]}"; do
        [ "$entry" = "$needle" ] && return 0
    done
    return 1
}

# ---------------------------------------------------------------------------
# Selection. Repository names are the positional arguments — required, and
# normalised: trailing slashes (shell tab-completion) are stripped, anything
# still carrying a path separator is refused, duplicates collapse with a
# warning. A malformed name that slipped through would bypass the retired
# check and propagate into the emitted records and the bracket text.
# ---------------------------------------------------------------------------
selected_repositories=()
declare -A selected_lookup

for argument in "$@"; do
    case "$argument" in
        --help|-h) usage 0 ;;
        -*) echo "FATAL: unknown flag $argument" >&2; usage 1 >&2 ;;
    esac
    repository_name="$argument"
    while [ "${repository_name%/}" != "$repository_name" ]; do
        repository_name="${repository_name%/}"
    done
    case "$repository_name" in
        */* | '')
            echo "FATAL: '$argument' is not a bare repository name; paths are not accepted." >&2
            exit 1 ;;
    esac
    if [ -n "${selected_lookup[$repository_name]:-}" ]; then
        echo "WARNING: $repository_name named more than once; using it once." >&2
        continue
    fi
    selected_lookup[$repository_name]=1
    selected_repositories+=("$repository_name")
done

if [ "${#selected_repositories[@]}" -eq 0 ]; then
    echo "FATAL: no repository named. This script requires an explicit repository list;" >&2
    echo "a whole-fleet entry is ../syneto-release-notes/acquire.sh, not this script." >&2
    exit 1
fi

cd "$projects_root" || { echo "FATAL: cannot enter $projects_root" >&2; exit 1; }

for repository in "${selected_repositories[@]}"; do
    if [ ! -e "$repository/.git" ]; then
        echo "FATAL: '$repository' is not a git repository under $projects_root." >&2
        exit 1
    fi
    if is_retired "$repository"; then
        echo "WARNING: $repository is on the retired list but was named explicitly — proceeding." >&2
    fi
done

# ---------------------------------------------------------------------------
# Candidate repositories, discovered exactly as the parent does: anything
# holding at least one exact central-<N>.<N> remote ref, plus the
# infrastructure repository. A retired repository stays excluded from
# discovery unless the operator named it. A SELECTED repository that discovery
# did not find (no central-<N>.<N> refs yet — a fresh clone, or a repository
# outside the release train) is force-added so it is still fetched and
# classified; if its pair does not resolve after the fetch that is fatal
# below, never a silent drop.
# ---------------------------------------------------------------------------
candidate_repositories=()
excluded_repositories=()
declare -A candidate_lookup

for candidate in */; do
    repository="${candidate%/}"
    # -e not -d: a linked worktree or submodule has .git as a file.
    [ -e "$repository/.git" ] || continue
    if [ "$repository" = "$infrastructure_repository" ]; then
        candidate_repositories+=("$repository")
        candidate_lookup[$repository]=1
        continue
    fi
    if git -C "$repository" for-each-ref --format='%(refname:short)' refs/remotes/origin/ 2>/dev/null \
        | grep -qE "$release_pattern"; then
        if is_retired "$repository" && [ -z "${selected_lookup[$repository]:-}" ]; then
            excluded_repositories+=("$repository")
        else
            candidate_repositories+=("$repository")
            candidate_lookup[$repository]=1
        fi
    fi
done

force_added_repositories=()
for repository in "${selected_repositories[@]}"; do
    [ -n "${candidate_lookup[$repository]:-}" ] && continue
    candidate_repositories+=("$repository")
    candidate_lookup[$repository]=1
    force_added_repositories+=("$repository")
done

# ---------------------------------------------------------------------------
# Fetch the WHOLE candidate fleet, exactly as the parent does. The pair
# derivation, the quorum guard, and the OUTSIDE bucket all read fleet refs, so
# fetching only the selected repositories would let any of the three go stale.
# A fetch failure in a SELECTED repository is fatal — its range is the release
# content. A failure elsewhere degrades only the OUTSIDE bucket and is
# reported as exactly that.
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

out_of_scope_fetch_failures=()
for failure in "${fetch_failures[@]}"; do
    failed_repository="${failure%%$'\t'*}"
    if [ -n "${selected_lookup[$failed_repository]:-}" ]; then
        echo "FATAL: fetch failed for selected repository $failed_repository:" >&2
        echo "  ${failure#*$'\t'}" >&2
        echo "A selected repository's range must be fresh; fix the fetch and re-run." >&2
        exit 1
    fi
    out_of_scope_fetch_failures+=("$failure")
done

# ---------------------------------------------------------------------------
# Branch pair. Explicit via SYNETO_NOTES_PAIR — validated for shape and
# ordering, mirroring promote.sh's SYNETO_PROMOTE_PAIR — or derived by numeric
# version sort across the fleet, exactly as the parent: central-2.9 sorts
# ABOVE central-2.10 lexically, so a plain sort picks the wrong pair.
# ---------------------------------------------------------------------------
if [ -n "${SYNETO_NOTES_PAIR:-}" ]; then
    read -r prod_branch dev_branch extra_field <<<"$SYNETO_NOTES_PAIR"
    if [ -z "${dev_branch:-}" ] || [ -n "${extra_field:-}" ]; then
        echo "FATAL: SYNETO_NOTES_PAIR must be exactly '<prod> <dev>'." >&2
        exit 1
    fi
    for branch in "$prod_branch" "$dev_branch"; do
        [[ "$branch" =~ $pair_branch_pattern ]] || {
            echo "FATAL: '$branch' is not a central-<N>.<N> branch name." >&2
            exit 1
        }
    done
    lower=$(printf '%s\n%s\n' "${prod_branch#central-}" "${dev_branch#central-}" \
        | sort -t. -k1,1n -k2,2n | head -1)
    [ "$lower" = "${prod_branch#central-}" ] || {
        echo "FATAL: pair is reversed — prod ($prod_branch) must be older than dev ($dev_branch)." >&2
        exit 1
    }
    pair_origin="operator-supplied (SYNETO_NOTES_PAIR)"
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
# PASS 1 — classify every candidate, fleet-wide, emitting nothing.
#   outcome 0  contributing (non-empty range)
#   outcome 1  pair does not resolve
#   outcome 2  pair resolves, range empty
#   outcome 3  range read failed (git error)
# The subject/body ticket split matches the parent: TICKETS ids come from
# subjects of the FULL log including merges; XREF quarantines body-only ids.
# ---------------------------------------------------------------------------
declare -A range_outcome range_total range_merges range_tip
declare -A range_tickets range_xref range_tag range_prod_ref range_dev_ref

classify_repository_range() {
    local repository="$1" prod_ref="$2" dev_ref="$3" tag="$4"
    range_tag[$repository]="$tag"
    range_prod_ref[$repository]="$prod_ref"
    range_dev_ref[$repository]="$dev_ref"

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

    range_total[$repository]="$total"
    range_merges[$repository]="$merges"
    range_tip[$repository]="$tip"
    range_tickets[$repository]="$(echo "$subject_tickets" | tr '\n' ' ')"
    range_xref[$repository]="$(echo "$crossref_tickets" | tr '\n' ' ')"
    return 0
}

contributing_repositories=()
empty_repositories=()
unresolved_repositories=()
failed_repositories=()
pair_resolved_count=0

for repository in "${candidate_repositories[@]}"; do
    if [ "$repository" = "$infrastructure_repository" ]; then
        classify_repository_range "$repository" \
            "origin/$infrastructure_prod_ref" "origin/$infrastructure_dev_ref" "platform"
    else
        classify_repository_range "$repository" \
            "origin/$prod_branch" "origin/$dev_branch" "product"
    fi
    outcome=$?
    range_outcome[$repository]="$outcome"
    case "$outcome" in
        0) contributing_repositories+=("$repository") ;;
        1) unresolved_repositories+=("$repository") ;;
        2) empty_repositories+=("$repository") ;;
        3) failed_repositories+=("$repository") ;;
    esac
    # Quorum arithmetic mirrors the parent: product repositories only, and only
    # those the parent's discovery would count — a retired repository re-added
    # because the operator named it stays out of the denominator, and so does
    # `central`, which runs on its own fixed refs.
    if [ "$repository" != "$infrastructure_repository" ] && ! is_retired "$repository" \
        && { [ "$outcome" -eq 0 ] || [ "$outcome" -eq 2 ]; }; then
        pair_resolved_count=$((pair_resolved_count + 1))
    fi
done

# ---------------------------------------------------------------------------
# Exit rules are TOTAL over the selected repositories: every selected
# repository must classify as contributing or empty. Outcome 1 or 3 for a
# selected repository is fatal — the parent buries these in advisory buckets
# because it is autonomous over the whole fleet, but here the operator asked
# for this repository by name, and exit 0 with no records for it would read as
# "nothing to describe" when the truth is "could not read it".
# ---------------------------------------------------------------------------
for repository in "${selected_repositories[@]}"; do
    case "${range_outcome[$repository]}" in
        1)
            echo "FATAL: selected repository $repository does not resolve" \
                 "${range_prod_ref[$repository]}..${range_dev_ref[$repository]}." >&2
            echo "Even after fetching it carries no such remote refs — it is outside this" >&2
            echo "release train (the bi-tool precedent), never cut this branch, or the pair is wrong." >&2
            exit 1 ;;
        3)
            echo "FATAL: selected repository $repository failed the range read (git error)." >&2
            echo "Treat as unknown, not as empty; inspect the clone and re-run." >&2
            exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Quorum guard, fleet-wide as in the parent. One scoped-only degradation: when
# no PRODUCT repository is selected (a `central`-only scope), the product pair
# governs nothing that is emitted, so a rollover elsewhere in the fleet must
# not abort the run — but it does make the OUT OF SCOPE bucket unreliable,
# which is worth a warning.
# ---------------------------------------------------------------------------
product_repository_selected=0
for repository in "${selected_repositories[@]}"; do
    [ "$repository" != "$infrastructure_repository" ] && product_repository_selected=1
done

if [ "${#unresolved_repositories[@]}" -gt "$pair_resolved_count" ]; then
    message="$pair_origin pair $prod_branch..$dev_branch resolves in $pair_resolved_count product repositories but fails in ${#unresolved_repositories[@]}"
    if [ "${SYNETO_ALLOW_MINORITY_PAIR:-0}" = "1" ]; then
        echo "WARNING: $message — proceeding under SYNETO_ALLOW_MINORITY_PAIR=1." >&2
    elif [ "$product_repository_selected" -eq 0 ]; then
        echo "WARNING: $message — proceeding because only $infrastructure_repository is selected" >&2
        echo "and it runs on its own fixed pair. The OUT OF SCOPE bucket may be unreliable." >&2
    else
        echo "FATAL: $message." >&2
        echo "Either a newly-cut release branch flipped the derivation, or the supplied pair is wrong." >&2
        echo "Re-run with the correct pair, or set SYNETO_ALLOW_MINORITY_PAIR=1 if a minority release is intended." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Empty selected ranges. The parent hard-fails only on total emptiness because
# it is autonomous; this script has an operator by definition — the repository
# set is their input — so ANY selected repository with an empty range means
# their mental model disagrees with git, and that disagreement is fatal unless
# explicitly waived. ALL selected ranges empty is fatal with no waiver.
# ---------------------------------------------------------------------------
describe_empty_range() {
    local repository="$1"
    if git -C "$repository" merge-base --is-ancestor \
        "${range_dev_ref[$repository]}" "${range_prod_ref[$repository]}" 2>/dev/null; then
        echo "already promoted — ${range_dev_ref[$repository]} is contained in ${range_prod_ref[$repository]}"
    else
        echo "nothing in this range"
    fi
}

contributing_selected_repositories=()
empty_selected_repositories=()
for repository in "${selected_repositories[@]}"; do
    if [ "${range_outcome[$repository]}" -eq 0 ]; then
        contributing_selected_repositories+=("$repository")
    else
        empty_selected_repositories+=("$repository")
    fi
done

if [ "${#contributing_selected_repositories[@]}" -eq 0 ]; then
    echo "FATAL: every selected repository has an empty range — there is nothing to describe:" >&2
    for repository in "${empty_selected_repositories[@]}"; do
        echo "  $repository: $(describe_empty_range "$repository")" >&2
    done
    echo "Either the release is already merged, the pair is wrong, or the scope is." >&2
    exit 1
fi

if [ "${#empty_selected_repositories[@]}" -gt 0 ]; then
    if [ "${SYNETO_ALLOW_EMPTY_SELECTION:-0}" = "1" ]; then
        for repository in "${empty_selected_repositories[@]}"; do
            echo "WARNING: selected repository $repository has an empty range" \
                 "($(describe_empty_range "$repository")) — proceeding without it under SYNETO_ALLOW_EMPTY_SELECTION=1." >&2
        done
    else
        echo "FATAL: selected repositories with empty ranges — the scope disagrees with git:" >&2
        for repository in "${empty_selected_repositories[@]}"; do
            echo "  $repository: $(describe_empty_range "$repository")" >&2
        done
        echo "Re-run with only the contributing repositories: ${contributing_selected_repositories[*]}" >&2
        echo "Or set SYNETO_ALLOW_EMPTY_SELECTION=1 to proceed without the empty ones." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# PASS 2 — emit. Selected repositories get full records; contributing
# repositories outside the scope get OUTSIDE records, whose ids exist so the
# skill can detect partial shipping and arbitrate the [platform] tag —
# deliberately NOT named TICKETS-anything, so a `grep '^TICKETS'` cannot drag
# out-of-scope ids into the entry.
# ---------------------------------------------------------------------------
echo "=== RELEASE PAIR ==="
printf 'prod\t%s\ndev\t%s\nsource\t%s\ninfra\t%s..%s\n' \
    "$prod_branch" "$dev_branch" "$pair_origin" \
    "$infrastructure_prod_ref" "$infrastructure_dev_ref"

echo
echo "=== SELECTED REPOSITORIES (operator-supplied scope) ==="
printf '%s\n' "${selected_repositories[@]}"

if [ "${#force_added_repositories[@]}" -gt 0 ]; then
    echo
    echo "=== FORCE-ADDED (selected but not discovered — carried no central-<N>.<N> refs before the fetch) ==="
    printf '%s\n' "${force_added_repositories[@]}"
fi

echo
echo "=== CONTRIBUTING SELECTED REPOSITORIES (the only release content) ==="
echo "# REPO<tab>name<tab>tag<tab>range<tab>commits<tab>merges<tab>tip-date"
echo "# TICKETS<tab>name<tab>space-separated ids from commit subjects"
echo "# XREF<tab>name<tab>body-only ids — cross-references to other tickets, not release content"
echo "# COMMIT<tab>name<tab>sha<tab>subject"
for repository in "${contributing_selected_repositories[@]}"; do
    range="${range_prod_ref[$repository]}..${range_dev_ref[$repository]}"
    printf 'REPO\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$repository" "${range_tag[$repository]}" "$range" \
        "${range_total[$repository]}" "${range_merges[$repository]}" "${range_tip[$repository]}"
    printf 'TICKETS\t%s\t%s\n' "$repository" "${range_tickets[$repository]}"
    printf 'XREF\t%s\t%s\n' "$repository" "${range_xref[$repository]}"
    git -C "$repository" log --no-merges --format="COMMIT%x09$repository%x09%h%x09%s" "$range" 2>/dev/null
done

echo
echo "=== OUT OF SCOPE (contributing, not selected — NOT release content) ==="
echo "# OUTSIDE<tab>name<tab>commits<tab>space-separated subject ids"
echo "# A selected TICKETS id that also appears in an OUTSIDE record is PARTIALLY"
echo "# SHIPPING: bracket only the selected repositories, qualify the entry text,"
echo "# and flag it in the provenance report. OUTSIDE ids never become entry"
echo "# content on their own and never promote an XREF id."
out_of_scope_contributing_count=0
for repository in "${contributing_repositories[@]}"; do
    [ -n "${selected_lookup[$repository]:-}" ] && continue
    printf 'OUTSIDE\t%s\t%s\t%s\n' \
        "$repository" "${range_total[$repository]}" "${range_tickets[$repository]}"
    out_of_scope_contributing_count=$((out_of_scope_contributing_count + 1))
done
if [ "$out_of_scope_contributing_count" -eq 0 ]; then
    echo "none"
fi

echo
echo "=== EMPTY RANGES — SELECTED (waived via SYNETO_ALLOW_EMPTY_SELECTION, yielded no records) ==="
if [ "${#empty_selected_repositories[@]}" -gt 0 ]; then
    for repository in "${empty_selected_repositories[@]}"; do
        printf '%s\t%s\n' "$repository" "$(describe_empty_range "$repository")"
    done
else
    echo "none"
fi

echo
echo "=== EMPTY RANGES — OUT OF SCOPE (pair resolves, no commits) ==="
out_of_scope_empty_count=0
for repository in "${empty_repositories[@]}"; do
    [ -n "${selected_lookup[$repository]:-}" ] && continue
    printf '%s\n' "$repository"
    out_of_scope_empty_count=$((out_of_scope_empty_count + 1))
done
if [ "$out_of_scope_empty_count" -eq 0 ]; then
    echo "none"
fi

# Selected repositories never appear in the two buckets below — outcome 1 or 3
# for a selected repository is fatal above.
echo
echo "=== PAIR DOES NOT RESOLVE — OUT OF SCOPE (verify these are retired, not stale clones) ==="
printf '%s\n' "${unresolved_repositories[@]:-none}"

echo
echo "=== RANGE READ FAILED — OUT OF SCOPE (git error — treat as unknown, not as empty) ==="
printf '%s\n' "${failed_repositories[@]:-none}"

echo
echo "=== EXCLUDED AS RETIRED (operator-configured; a retired repository named explicitly is emitted above instead, with a warning) ==="
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
    if [ -n "${selected_lookup[$repository]:-}" ]; then
        status="SELECTED"
    elif [ "${range_outcome[$repository]}" -eq 0 ]; then
        status="contributing-out-of-scope"
    else
        status="not-contributing"
    fi
    printf '%s\t%s uncommitted entries\t%s\n' "$repository" "$dirty_entries" "$status"
    dirty_found=1
done
if [ "$dirty_found" -eq 0 ]; then
    echo "none"
fi

echo
echo "=== FETCH FAILURES — OUT OF SCOPE (degrades only the OUTSIDE bucket; a selected fetch failure is fatal) ==="
printf '%s\n' "${out_of_scope_fetch_failures[@]:-none}"

echo
echo "=== SUMMARY ==="
printf 'selected_repositories\t%s\n' "${#selected_repositories[@]}"
printf 'contributing_selected_repositories\t%s\n' "${#contributing_selected_repositories[@]}"
printf 'out_of_scope_contributing_repositories\t%s\n' "$out_of_scope_contributing_count"
printf 'candidate_repositories\t%s\n' "${#candidate_repositories[@]}"
printf 'product_repos_resolving_pair\t%s\n' "$pair_resolved_count"

exit 0
