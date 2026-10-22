"""Work out where each ticket of a writing pipeline stands, from the files on disk.

Prints, per ticket id, the next stage to run (write, review1, fix1, review2, fix2, done), so a
stopped or hung pipeline is relaunched from there instead of with resumeFromRunId (the workflow
cache matches calls by position, so a resumed run with parallel agents redoes finished work).

Usage: python3 pipeline_state.py <run dir> <stories|tasks> <id> [<id> ...]
"""
import os
import re
import sys

NO_FINDINGS = re.compile(r"\bno findings\b", re.IGNORECASE)


def has_findings(review_path):
    text = open(review_path, encoding="utf-8").read()
    return not NO_FINDINGS.search(text[:2000])


def next_stage(run, kind, ticket_id):
    draft = os.path.join(run, kind, f"{ticket_id}.md")
    reviews = os.path.join(run, "reviews", kind)
    if not os.path.exists(draft):
        return "write"
    for round_ in (1, 2):
        review = os.path.join(reviews, f"{ticket_id}-r{round_}.md")
        fixes = os.path.join(reviews, f"{ticket_id}-r{round_}-fixes.md")
        if not os.path.exists(review):
            return f"review{round_}"
        if has_findings(review) and not os.path.exists(fixes):
            return f"fix{round_}"
    return "done"


if __name__ == "__main__":
    run_dir, ticket_kind, *ids = sys.argv[1:]
    for ticket in ids:
        print(ticket, next_stage(run_dir, ticket_kind, ticket))
