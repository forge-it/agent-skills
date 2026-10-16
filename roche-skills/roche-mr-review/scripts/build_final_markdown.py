"""Write <run>/review-mr-<iid>.md, the file sent to the developer.

It holds only the findings that have a note file in notes/ (the ones the operator picked),
taken from the synthesized ledger, renumbered 1..N in ledger order, with the
ledger-internal fields dropped.

Usage: python3 -B build_final_markdown.py <run directory>
"""

import argparse
import re
import sys
from pathlib import Path

from review_run import NOTES_DIRECTORY_NAME, SYNTHESIZED_LEDGER_FILE_NAME, load_review_notes, load_review_run

FINDING_HEADER_PATTERN = re.compile(r"^### Finding (\d+) — (.+?)\s*$", re.MULTILINE)
SECTION_HEADER_PATTERN = re.compile(r"^## ", re.MULTILINE)
FINDING_REFERENCE_PATTERN = re.compile(r"\b(finding) (\d+)\b", re.IGNORECASE)
UNLISTED_REFERENCE_PARENTHETICAL_PATTERN = re.compile(r"\s*\((?:see |also )?finding (\d+)\)", re.IGNORECASE)
PLURAL_REFERENCE_PATTERN = re.compile(r"\bfindings \d+", re.IGNORECASE)
INTERNAL_FIELD_PREFIXES = ("**Anchor:**", "**Found by:**")
TRAILING_RULE = "---"


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argument_parser.add_argument("run_directory", type=Path)
    arguments = argument_parser.parse_args()

    review_run = load_review_run(arguments.run_directory)
    ledger_file = arguments.run_directory / SYNTHESIZED_LEDGER_FILE_NAME
    if not ledger_file.exists():
        sys.exit(f"{ledger_file} not found: run the synthesizer first")
    ledger_findings = read_ledger_findings(ledger_file.read_text())
    picked_ledger_numbers = sorted(review_note.finding for review_note in load_review_notes(arguments.run_directory))
    if not picked_ledger_numbers:
        sys.exit(
            f"no note files in {arguments.run_directory / NOTES_DIRECTORY_NAME}: the developer file holds the posted findings"
        )
    missing_ledger_numbers = [
        picked_ledger_number
        for picked_ledger_number in picked_ledger_numbers
        if picked_ledger_number not in ledger_findings
    ]
    if missing_ledger_numbers:
        sys.exit(f"notes exist for findings {missing_ledger_numbers}, which {ledger_file.name} does not contain")

    new_numbers = {
        picked_ledger_number: position for position, picked_ledger_number in enumerate(picked_ledger_numbers, start=1)
    }
    reference_warnings = []
    count = len(picked_ledger_numbers)
    introduction = (
        "This finding is worth fixing before merge. It is also posted as a review note on the MR,"
        if count == 1
        else f"These {count} findings are worth fixing before merge. Each one is also posted as a review note on the MR,"
    )
    sections = [
        f"# Review of !{review_run.merge_request_iid} — {review_run.title}",
        f"MR: {review_run.web_url}",
        f"{introduction} so please reply in the GitLab threads.",
    ]
    for picked_ledger_number in picked_ledger_numbers:
        heading, body = ledger_findings[picked_ledger_number]
        developer_body = renumber_references(
            "\n".join(
                body_line for body_line in body.splitlines() if not body_line.startswith(INTERNAL_FIELD_PREFIXES)
            ),
            new_numbers,
            reference_warnings,
        )
        sections.append(f"### Finding {new_numbers[picked_ledger_number]} — {heading}\n{developer_body}")

    output_file = arguments.run_directory / f"review-mr-{review_run.merge_request_iid}.md"
    output_file.write_text("\n\n".join(sections) + "\n")
    print(f"wrote {output_file} with {count} findings (ledger {', '.join(map(str, picked_ledger_numbers))})")
    for reference_warning in reference_warnings:
        print(f"WARNING: {reference_warning} — edit it by hand before sending")


def read_ledger_findings(ledger_text: str) -> dict[int, tuple[str, str]]:
    findings = {}
    finding_headers = list(FINDING_HEADER_PATTERN.finditer(ledger_text))
    for index, finding_header in enumerate(finding_headers):
        body_end = finding_headers[index + 1].start() if index + 1 < len(finding_headers) else len(ledger_text)
        section_header = SECTION_HEADER_PATTERN.search(ledger_text, finding_header.end(), body_end)
        if section_header:
            body_end = section_header.start()
        body = ledger_text[finding_header.end() : body_end].strip().removesuffix(TRAILING_RULE).strip()
        findings[int(finding_header.group(1))] = (finding_header.group(2), body)
    return findings


def renumber_references(body: str, new_numbers: dict[int, int], reference_warnings: list[str]) -> str:
    def drop_unlisted_parenthetical(reference: re.Match) -> str:
        return reference.group(0) if int(reference.group(1)) in new_numbers else ""

    def renumber(reference: re.Match) -> str:
        ledger_number = int(reference.group(2))
        if ledger_number in new_numbers:
            return f"{reference.group(1)} {new_numbers[ledger_number]}"
        reference_warnings.append(f"a finding mentions ledger finding {ledger_number}, which is not in this file")
        return reference.group(0)

    for plural_reference in PLURAL_REFERENCE_PATTERN.findall(body):
        reference_warnings.append(f"'{plural_reference}…' is not renumbered automatically")
    body = UNLISTED_REFERENCE_PARENTHETICAL_PATTERN.sub(drop_unlisted_parenthetical, body)
    return FINDING_REFERENCE_PATTERN.sub(renumber, body)


if __name__ == "__main__":
    main()
