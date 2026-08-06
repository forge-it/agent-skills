#!/usr/bin/env bash
#
# Promote a Syneto Central release: merge the dev branch into the prod branch
# across every contributing repository, and push.
#
# Run ONLY after the release notes entry has been published and accepted. The
# merge empties the prod..dev range, so the notes can no longer be regenerated
# from git afterwards.
#
# Usage:
#   ./promote.sh                      # --check (default): preflight only
#   ./promote.sh --merge              # preflight, then merge locally; no push
#   ./promote.sh --push               # preflight, merge, and push to origin
#   ./promote.sh --push repo-a repo-b # restrict to named repositories
#   ./promote.sh --help
#
# Mode flags are mutually exclusive; passing two is an error rather than
# last-one-wins, because `--check --push` must never silently push.
#
# Environment:
#   SYNETO_PROJECTS_ROOT         defaults to /home/cristi/Projects
#   SYNETO_SKIP_FETCH            reuse local refs. REFUSED in --merge/--push:
#                                a stale ref promotes a tree nobody reviewed.
#   SYNETO_PROMOTE_PAIR          "<prod> <dev>", validated for shape and order
#   SYNETO_INCLUDE_CENTRAL       1 to also promote the `central` IaaC repo,
#                                which uses production-on-prem..dev-on-prem
#   SYNETO_ALLOW_MINORITY_PAIR   1 to downgrade the quorum guard to a warning
#   SYNETO_PROMOTE_CONFIRM       must equal the dev branch name for --push to
#                                proceed; the operator consent gate
#
# Exit codes:
#   0  clean
#   1  refused before any repository was modified — read stderr
#   2  one or more repositories failed mid-run; the release is PARTIAL

set -uo pipefail

projects_root="${SYNETO_PROJECTS_ROOT:-/home/cristi/Projects}"
infrastructure_repository="central"
infrastructure_prod_ref="production-on-prem"
infrastructure_dev_ref="dev-on-prem"
# Kept in sync BY HAND with the identical list in
# ../syneto-release-notes/acquire.sh. The two skills must agree on what is out
# of the release; if you change one, change the other in the same commit.
retired_repositories=("central-vat-searcher")
mode=""
release_pattern='^central-[0-9]+\.[0-9]+$'

usage() {
    sed -n '3,40p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

is_retired() {
    local needle="$1" entry
    for entry in "${retired_repositories[@]}"; do
        [ "$entry" = "$needle" ] && return 0
    done
    return 1
}

# Capture stderr so failures report what git actually said. Diagnosing a push
# failure as "someone else pushed" hides protected branches, dead credentials,
# and pre-receive hooks behind a message that invites a pointless retry.
# Combined stdout+stderr: `git merge` writes "CONFLICT (add/add): ..." to
# STDOUT, so capturing stderr alone reports conflicts with an empty reason —
# and a conflict is the one failure preflight cannot pre-empt.
git_error=""
try_git() {
    local repository="$1"; shift
    git_error=$(git -C "$repository" "$@" 2>&1 | tr '\n' ' ' | cut -c1-300)
    return "${PIPESTATUS[0]}"
}

selected_repositories=()
for argument in "$@"; do
    case "$argument" in
        --help|-h) usage 0 ;;
        --check|--merge|--push)
            candidate_mode="${argument#--}"
            if [ -n "$mode" ] && [ "$mode" != "$candidate_mode" ]; then
                echo "FATAL: --$mode and $argument are mutually exclusive." >&2
                exit 1
            fi
            mode="$candidate_mode" ;;
        -*) echo "FATAL: unknown flag $argument" >&2; usage 1 >&2 ;;
        *) selected_repositories+=("$argument") ;;
    esac
done
mode="${mode:-check}"

cd "$projects_root" || { echo "FATAL: cannot enter $projects_root" >&2; exit 1; }

if [ "$mode" != "check" ] && [ "${SYNETO_SKIP_FETCH:-0}" = "1" ]; then
    echo "FATAL: SYNETO_SKIP_FETCH is set. Refusing to $mode from possibly stale refs." >&2
    echo "A stale origin/dev promotes an older tree than the operator reviewed." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Branch pair. Numeric version sort: central-2.9 sorts ABOVE central-2.10
# lexically, so a plain sort inverts the pair. Retired repositories are
# excluded first so a stray high version in a dead clone cannot move the pair.
# ---------------------------------------------------------------------------
product_candidates=()
excluded_repositories=()
for candidate in */; do
    repository="${candidate%/}"
    [ -e "$repository/.git" ] || continue
    [ "$repository" = "$infrastructure_repository" ] && continue
    git -C "$repository" for-each-ref --format='%(refname:short)' refs/remotes/origin/ 2>/dev/null \
        | grep -qE "^origin/central-[0-9]+\.[0-9]+$" || continue
    if is_retired "$repository"; then
        excluded_repositories+=("$repository")
    else
        product_candidates+=("$repository")
    fi
done

# ---------------------------------------------------------------------------
# Fetch BEFORE selecting, not inside the preflight loop. Selection reads
# origin/prod..origin/dev, so fetching only what was already selected makes a
# repository with stale local refs permanently invisible: empty range, never
# selected, never fetched, still stale on the next run. It would then be
# missing from a release the accepted notes already promised.
# ---------------------------------------------------------------------------
fetch_failures=()
if [ "${SYNETO_SKIP_FETCH:-0}" != "1" ]; then
    fetch_failure_log="$(mktemp)" || { echo "FATAL: cannot create temp file" >&2; exit 1; }
    trap 'rm -f "$fetch_failure_log"' EXIT
    fetch_targets=("${product_candidates[@]}")
    [ -e "$infrastructure_repository/.git" ] && fetch_targets+=("$infrastructure_repository")
    running=0
    for repository in "${fetch_targets[@]}"; do
        {
            fetch_error=$(git -C "$repository" fetch --quiet --prune origin 2>&1) \
                || printf '%s\t%s\n' "$repository" "${fetch_error//[$'\n\t']/ }" >>"$fetch_failure_log"
        } &
        running=$((running + 1))
        if [ "$running" -ge 12 ]; then wait; running=0; fi
    done
    wait
    mapfile -t fetch_failures <"$fetch_failure_log"
fi

if [ -n "${SYNETO_PROMOTE_PAIR:-}" ]; then
    read -r prod_branch dev_branch extra_field <<<"$SYNETO_PROMOTE_PAIR"
    if [ -z "${dev_branch:-}" ] || [ -n "${extra_field:-}" ]; then
        echo "FATAL: SYNETO_PROMOTE_PAIR must be exactly '<prod> <dev>'." >&2; exit 1
    fi
    for branch in "$prod_branch" "$dev_branch"; do
        [[ "$branch" =~ $release_pattern ]] || {
            echo "FATAL: '$branch' is not a central-<N>.<N> branch name." >&2; exit 1; }
    done
    # Order matters absolutely: reversed, this merges prod into dev and pushes
    # the dev branch — a backwards promotion that reports success.
    lower=$(printf '%s\n%s\n' "${prod_branch#central-}" "${dev_branch#central-}" \
        | sort -t. -k1,1n -k2,2n | head -1)
    [ "$lower" = "${prod_branch#central-}" ] || {
        echo "FATAL: pair is reversed — prod ($prod_branch) must be older than dev ($dev_branch)." >&2
        exit 1; }
    pair_origin="operator-supplied"
else
    mapfile -t sorted_versions < <(
        for repository in "${product_candidates[@]}"; do
            git -C "$repository" for-each-ref --format='%(refname:short)' refs/remotes/origin/ 2>/dev/null \
                | grep -E "^origin/central-[0-9]+\.[0-9]+$" | sed 's|^origin/central-||'
        done | sort -u -t. -k1,1n -k2,2n
    )
    if [ "${#sorted_versions[@]}" -lt 2 ]; then
        echo "FATAL: need two central-<N>.<N> versions to form a pair." >&2; exit 1
    fi
    dev_branch="central-${sorted_versions[$((${#sorted_versions[@]} - 1))]}"
    prod_branch="central-${sorted_versions[$((${#sorted_versions[@]} - 2))]}"
    pair_origin="derived-by-numeric-version-sort"
fi

# ---------------------------------------------------------------------------
# Quorum guard, mirroring acquire.sh. At a major rollover the first team to cut
# central-2.11 flips the pair fleet-wide; every other repository then fails to
# resolve it and is skipped, yielding a one-repository "release" that
# preflights clean and pushes.
# ---------------------------------------------------------------------------
pair_resolves=0
pair_fails=0
for repository in "${product_candidates[@]}"; do
    if git -C "$repository" rev-parse --verify --quiet "origin/$prod_branch" >/dev/null \
        && git -C "$repository" rev-parse --verify --quiet "origin/$dev_branch" >/dev/null; then
        pair_resolves=$((pair_resolves + 1))
    else
        pair_fails=$((pair_fails + 1))
    fi
done

if [ "$pair_fails" -gt "$pair_resolves" ]; then
    message="$pair_origin pair $prod_branch..$dev_branch resolves in $pair_resolves repositories but fails in $pair_fails"
    if [ "${SYNETO_ALLOW_MINORITY_PAIR:-0}" = "1" ]; then
        echo "WARNING: $message — proceeding under SYNETO_ALLOW_MINORITY_PAIR=1." >&2
    else
        echo "FATAL: $message." >&2
        echo "Either a newly-cut release branch flipped the derivation, or the pair is wrong." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Selection. Per-repository refs, because `central` runs on its own pair.
# ---------------------------------------------------------------------------
declare -A repository_prod_ref repository_dev_ref

register_repository() {
    local repository="$1" prod_ref="$2" dev_ref="$3"
    git -C "$repository" rev-parse --verify --quiet "$prod_ref" >/dev/null || return 1
    git -C "$repository" rev-parse --verify --quiet "$dev_ref" >/dev/null || return 1
    repository_prod_ref["$repository"]="$prod_ref"
    repository_dev_ref["$repository"]="$dev_ref"
    return 0
}

resolved_repositories=()
if [ "${#selected_repositories[@]}" -gt 0 ]; then
    for repository in "${selected_repositories[@]}"; do
        [ -e "$repository/.git" ] \
            || { echo "FATAL: '$repository' is not a git repository under $projects_root." >&2; exit 1; }
        is_retired "$repository" \
            && echo "WARNING: $repository is on the retired list but was named explicitly." >&2
        if [ "$repository" = "$infrastructure_repository" ]; then
            register_repository "$repository" \
                "origin/$infrastructure_prod_ref" "origin/$infrastructure_dev_ref" \
                || { echo "FATAL: $repository does not resolve its on-prem pair." >&2; exit 1; }
        else
            register_repository "$repository" "origin/$prod_branch" "origin/$dev_branch" \
                || { echo "FATAL: $repository does not resolve $prod_branch..$dev_branch." >&2; exit 1; }
        fi
        resolved_repositories+=("$repository")
    done
else
    for repository in "${product_candidates[@]}"; do
        register_repository "$repository" "origin/$prod_branch" "origin/$dev_branch" || continue
        count=$(git -C "$repository" rev-list --count \
            "${repository_prod_ref[$repository]}..${repository_dev_ref[$repository]}" 2>/dev/null)
        [ "${count:-0}" -gt 0 ] && resolved_repositories+=("$repository")
    done
    if [ "${SYNETO_INCLUDE_CENTRAL:-0}" = "1" ] && [ -e "$infrastructure_repository/.git" ]; then
        if register_repository "$infrastructure_repository" \
            "origin/$infrastructure_prod_ref" "origin/$infrastructure_dev_ref"; then
            count=$(git -C "$infrastructure_repository" rev-list --count \
                "origin/$infrastructure_prod_ref..origin/$infrastructure_dev_ref" 2>/dev/null)
            if [ "${count:-0}" -gt 0 ]; then
                resolved_repositories+=("$infrastructure_repository")
            else
                echo "NOTE: $infrastructure_repository was requested but its range" \
                     "$infrastructure_prod_ref..$infrastructure_dev_ref is empty; nothing to promote there." >&2
            fi
        else
            echo "WARNING: SYNETO_INCLUDE_CENTRAL=1 but $infrastructure_repository does not resolve" \
                 "$infrastructure_prod_ref..$infrastructure_dev_ref; it was NOT included." >&2
        fi
    fi
fi

if [ "${#resolved_repositories[@]}" -eq 0 ]; then
    echo "FATAL: nothing to promote — no repository has commits in $prod_branch..$dev_branch." >&2
    echo "The release may already be promoted." >&2
    exit 1
fi

echo "=== PLAN ==="
printf 'mode\t%s\npair\t%s..%s (%s)\n' "$mode" "$prod_branch" "$dev_branch" "$pair_origin"
for repository in "${resolved_repositories[@]}"; do
    prod_ref="${repository_prod_ref[$repository]}"
    dev_ref="${repository_dev_ref[$repository]}"
    ahead=$(git -C "$repository" rev-list --count "$prod_ref..$dev_ref" 2>/dev/null)
    tickets=$(git -C "$repository" log --format='%s' "$prod_ref..$dev_ref" 2>/dev/null \
        | grep -oE '\b(SYN|CENTRAL)-[0-9]+' | sort -u | tr '\n' ' ')
    # Name the pair per repository: `central` promotes its own on-prem refs,
    # and a header-only pair would misdescribe it.
    printf 'repo\t%s\t%s..%s\t%s commits\t%s\n' \
        "$repository" "${prod_ref#origin/}" "${dev_ref#origin/}" "${ahead:-?}" \
        "${tickets:-NO TICKETS — verify this belongs in the release}"
done
# Retirement must be visible: the notes skill treats a silently dropped
# repository as a defect, and the two halves must agree on what shipped.
[ "${#excluded_repositories[@]}" -gt 0 ] \
    && printf 'excluded-as-retired\t%s\n' "$(IFS=' '; echo "${excluded_repositories[*]}")"
[ "${#fetch_failures[@]}" -gt 0 ] \
    && printf 'fetch-failures\t%s\n' "${#fetch_failures[@]}"

# ---------------------------------------------------------------------------
# Preflight. Every repository is checked before any is modified.
# ---------------------------------------------------------------------------
echo
echo "=== PREFLIGHT ==="
blockers=0
declare -A original_branch repository_action repository_note

for repository in "${resolved_repositories[@]}"; do
    problems=()
    prod_ref="${repository_prod_ref[$repository]}"
    dev_ref="${repository_dev_ref[$repository]}"
    local_prod="${prod_ref#origin/}"
    action="merge"

    if ! original_branch["$repository"]=$(git -C "$repository" symbolic-ref --quiet --short HEAD 2>/dev/null); then
        problems+=("detached HEAD — check out a branch first")
        original_branch["$repository"]=""
    fi

    for failure in "${fetch_failures[@]}"; do
        [ "${failure%%$'\t'*}" = "$repository" ] && problems+=("fetch failed: ${failure#*$'\t'}")
    done

    if [ -n "$(git -C "$repository" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        problems+=("tracked files modified — commit, stash, or exclude this repo")
    fi

    # The prod branch checked out in a second worktree cannot be switched to.
    if git -C "$repository" worktree list --porcelain 2>/dev/null \
        | grep -qx "branch refs/heads/$local_prod"; then
        if [ "${original_branch[$repository]}" != "$local_prod" ]; then
            problems+=("$local_prod is checked out in another worktree")
        fi
    fi

    if [ "${#problems[@]}" -eq 0 ]; then
        if git -C "$repository" rev-parse --verify --quiet "refs/heads/$local_prod" >/dev/null; then
            if git -C "$repository" merge-base --is-ancestor "refs/heads/$local_prod" "$prod_ref" 2>/dev/null; then
                action="merge"
            elif git -C "$repository" merge-base --is-ancestor "$prod_ref" "refs/heads/$local_prod" 2>/dev/null; then
                # Local prod is ahead of origin. That is the state an earlier
                # --merge or a failed push leaves, and it is resumable — but
                # ONLY if everything extra is a promotion merge. Containment of
                # origin/dev is not sufficient: an ordinary commit sitting on
                # top of the merge also "contains" it, and would ship to
                # production unreviewed. Any non-merge extra is foreign.
                foreign=$(git -C "$repository" rev-list --no-merges --count \
                    "refs/heads/$local_prod" "^$prod_ref" "^$dev_ref" 2>/dev/null)
                if [ "${foreign:-0}" -gt 0 ]; then
                    problems+=("local $local_prod carries $foreign commit(s) that are on neither origin branch — not part of this promotion")
                elif git -C "$repository" merge-base --is-ancestor "$dev_ref" "refs/heads/$local_prod" 2>/dev/null; then
                    action="push-only"
                    # A hand-run `merge --ff-only origin/dev` leaves no merge
                    # commit, so `git revert -m 1` cannot pull the release back.
                    if [ "$(git -C "$repository" rev-list --count --merges \
                        "refs/heads/$local_prod" "^$prod_ref" 2>/dev/null)" = "0" ]; then
                        repository_note["$repository"]="fast-forwarded, no merge commit — revert -m 1 will not work"
                    fi
                else
                    # Local prod holds a promotion merge, but dev has moved on
                    # since. Re-merge the new tip rather than blocking: this is
                    # the routine race, not a divergence.
                    action="remerge"
                fi
            else
                problems+=("local $local_prod has diverged from $prod_ref — merge $prod_ref by hand, then re-run")
            fi
        fi
    fi

    if [ "${#problems[@]}" -eq 0 ] && [ "$action" != "push-only" ]; then
        if ! git -C "$repository" merge-tree --write-tree "$prod_ref" "$dev_ref" >/dev/null 2>&1; then
            problems+=("merge conflicts or unrelated histories — resolve by hand")
        fi
        # merge-tree is a pure object-database operation and cannot see the
        # worktree. An untracked file that the incoming merge tracks passes
        # here and then aborts the real merge.
        #
        # Intersect the two path sets rather than passing paths as arguments:
        # a large release overflows ARG_MAX and the failure is swallowed,
        # degrading the check to "never any collisions". -z avoids C-quoting,
        # which makes non-ASCII paths match nothing.
        collisions=$(comm -12 \
            <(git -C "$repository" diff -z --name-only "$prod_ref" "$dev_ref" 2>/dev/null | tr '\0' '\n' | sort -u) \
            <(git -C "$repository" ls-files --others --exclude-standard -z 2>/dev/null | tr '\0' '\n' | sort -u) \
            2>/dev/null | head -3 | tr '\n' ' ')
        [ -n "$collisions" ] && problems+=("untracked files would be overwritten: $collisions")

        # An untracked FILE where the merge adds a DIRECTORY of the same name
        # also aborts the merge, and a plain path intersection cannot see it.
        directory_collisions=$(comm -12 \
            <(git -C "$repository" diff -z --name-only "$prod_ref" "$dev_ref" 2>/dev/null | tr '\0' '\n' \
                | awk -F/ 'NF>1{p="";for(i=1;i<NF;i++){p=p (i>1?"/":"") $i; print p}}' | sort -u) \
            <(git -C "$repository" ls-files --others --exclude-standard -z 2>/dev/null | tr '\0' '\n' | sort -u) \
            2>/dev/null | head -2 | tr '\n' ' ')
        [ -n "$directory_collisions" ] \
            && problems+=("untracked file blocks an incoming directory: $directory_collisions")
    fi

    if [ "${#problems[@]}" -eq 0 ]; then
        repository_action["$repository"]="$action"
        printf 'OK      %-24s %-10s on %-18s %s\n' \
            "$repository" "$action" "${original_branch[$repository]}" \
            "${repository_note[$repository]:-}"
    else
        printf 'BLOCK   %-24s %s\n' "$repository" "$(printf '%s' "$(IFS='|'; echo "${problems[*]}")" | sed 's/|/; /g')"
        blockers=$((blockers + 1))
    fi
done

if [ "$blockers" -gt 0 ]; then
    echo
    echo "FATAL: $blockers repository(ies) blocked. Nothing was modified." >&2
    echo "Fix them, or name only the healthy repositories as arguments." >&2
    exit 1
fi

if [ "$mode" = "check" ]; then
    echo
    echo "Preflight clean. STOP HERE and show this plan to the operator."
    echo "Only after they approve, re-run with --merge (local) or --push"
    echo "(with SYNETO_PROMOTE_CONFIRM=$dev_branch)."
    exit 0
fi

if [ "$mode" = "push" ] && [ "${SYNETO_PROMOTE_CONFIRM:-}" != "$dev_branch" ]; then
    echo
    echo "FATAL: --push requires SYNETO_PROMOTE_CONFIRM=$dev_branch." >&2
    echo "This gate exists so a push to production is always a deliberate act." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Execute. A trap restores the checkout if the run is interrupted, so Ctrl-C
# never strands a repository on the prod branch with no report.
# ---------------------------------------------------------------------------
current_repository=""
restore_branch=""
# Report what actually happened. Claiming "aborted, restored" unconditionally is
# worse than saying nothing: a leftover index.lock makes both steps fail, and a
# push that already landed was never aborted at all.
on_interrupt() {
    if [ -n "$current_repository" ]; then
        local abort_note restore_note landed_branch
        if git -C "$current_repository" rev-parse --verify --quiet MERGE_HEAD >/dev/null 2>&1; then
            if git -C "$current_repository" merge --abort 2>/dev/null; then
                abort_note="merge aborted"
            else
                abort_note="MERGE ABORT FAILED — repository left mid-merge"
            fi
        else
            abort_note="no merge in progress"
        fi
        if [ -n "$restore_branch" ]; then
            if git -C "$current_repository" switch --quiet "$restore_branch" 2>/dev/null; then
                restore_note="restored to $restore_branch"
            else
                landed_branch=$(git -C "$current_repository" branch --show-current 2>/dev/null)
                restore_note="COULD NOT RESTORE $restore_branch — left on ${landed_branch:-unknown}"
            fi
        else
            restore_note="no branch to restore"
        fi
        echo >&2
        echo "INTERRUPTED during $current_repository: $abort_note; $restore_note." >&2
        echo "A push for this repository may already have landed — verify before re-running." >&2
        echo "The release is PARTIAL. Re-run to resume." >&2
    fi
    exit 2
}
trap on_interrupt INT TERM

echo
echo "=== $([ "$mode" = push ] && echo "MERGE AND PUSH" || echo "MERGE (local only)") ==="
failures=0
noops=0
promoted=0

for repository in "${resolved_repositories[@]}"; do
    current_repository="$repository"
    restore_branch="${original_branch[$repository]}"
    prod_ref="${repository_prod_ref[$repository]}"
    dev_ref="${repository_dev_ref[$repository]}"
    local_prod="${prod_ref#origin/}"
    action="${repository_action[$repository]}"
    failed=""

    prod_before=$(git -C "$repository" rev-parse --verify --quiet "refs/heads/$local_prod" 2>/dev/null \
        || git -C "$repository" rev-parse --verify --quiet "$prod_ref" 2>/dev/null)

    try_git "$repository" switch "$local_prod" || failed="cannot switch to $local_prod: $git_error"

    # Only the plain `merge` action is behind origin and needs the catch-up.
    if [ -z "$failed" ] && [ "$action" = "merge" ]; then
        try_git "$repository" merge --ff-only "$prod_ref" \
            || failed="cannot fast-forward $local_prod to origin: $git_error"
    fi

    if [ -z "$failed" ] && [ "$action" != "push-only" ]; then
        # --no-ff so a promotion is always an auditable merge commit that
        # `git revert -m 1` can undo. A fast-forward would leave nothing to
        # revert if the release has to be pulled back.
        if ! try_git "$repository" merge --no-ff --no-edit "$dev_ref"; then
            merge_error="$git_error"
            git -C "$repository" merge --abort 2>/dev/null
            failed="merge failed and was aborted: $merge_error"
        fi
    fi

    if [ -z "$failed" ] && [ "$mode" = "push" ]; then
        try_git "$repository" push origin "$local_prod" \
            || failed="push failed: $git_error"
    fi

    [ -n "$restore_branch" ] && git -C "$repository" switch --quiet "$restore_branch" 2>/dev/null

    if [ -n "$failed" ]; then
        printf 'FAIL    %-24s %s\n' "$repository" "$failed"
        failures=$((failures + 1))
        continue
    fi

    prod_after=$(git -C "$repository" rev-parse --verify --quiet "refs/heads/$local_prod" 2>/dev/null)

    # A push-only repository was already merged by an earlier run. In merge
    # mode there is nothing left to do; calling that "MERGED" and counting it
    # as promoted would report work that did not happen.
    if [ "$action" = "push-only" ]; then
        if [ "$mode" = "push" ]; then
            printf 'PUSHED  %-24s %s (merge was already local)\n' "$repository" "${prod_after:0:8}"
            promoted=$((promoted + 1))
        else
            printf 'PENDING %-24s already merged locally; nothing to do until --push\n' "$repository"
            noops=$((noops + 1))
        fi
        continue
    fi

    if [ "$prod_before" = "$prod_after" ]; then
        printf 'NO-OP   %-24s already up to date, nothing promoted\n' "$repository"
        noops=$((noops + 1))
        continue
    fi

    if [ "$mode" = "push" ]; then
        # Re-fetch dev before measuring. A push updates the local origin/prod
        # ref, which would otherwise make the range arithmetically 0 always and
        # hide work a teammate landed on dev mid-run. A failed fetch must not
        # masquerade as a clean result — that is the same false all-clear.
        if git -C "$repository" fetch --quiet origin "$local_prod" "${dev_ref#origin/}" 2>/dev/null; then
            remaining=$(git -C "$repository" rev-list --count "$prod_ref..$dev_ref" 2>/dev/null)
            if [ "${remaining:-0}" -gt 0 ]; then
                printf 'DONE*   %-24s %s -> %s, but %s NEW commit(s) landed on %s mid-run\n' \
                    "$repository" "${prod_before:0:8}" "${prod_after:0:8}" "$remaining" "${dev_ref#origin/}"
            else
                printf 'DONE    %-24s %s -> %s\n' "$repository" "${prod_before:0:8}" "${prod_after:0:8}"
            fi
        else
            printf 'DONE?   %-24s %s -> %s, race check UNAVAILABLE (fetch failed)\n' \
                "$repository" "${prod_before:0:8}" "${prod_after:0:8}"
        fi
    else
        printf 'MERGED  %-24s %s -> %s (not pushed)\n' \
            "$repository" "${prod_before:0:8}" "${prod_after:0:8}"
    fi
    promoted=$((promoted + 1))
done

current_repository=""
trap - INT TERM

echo
echo "=== SUMMARY ==="
printf 'promoted\t%s\nno_op\t%s\nfailed\t%s\n' "$promoted" "$noops" "$failures"

if [ "$failures" -gt 0 ]; then
    echo "FATAL: $failures repository(ies) failed. The release is PARTIALLY promoted." >&2
    echo "Re-run: merged-but-unpushed repositories resume as push-only." >&2
    exit 2
fi

if [ "$mode" = "merge" ]; then
    echo "Local merges only. Re-run with --push (and SYNETO_PROMOTE_CONFIRM=$dev_branch)"
    echo "to publish them; those repositories will resume as push-only."
fi
[ "$mode" = "push" ] && echo "Any DONE* line above means work landed on $dev_branch mid-run and did NOT ship."
exit 0
