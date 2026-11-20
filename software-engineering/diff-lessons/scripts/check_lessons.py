#!/usr/bin/env python3
"""Check a diff-lessons draft before it is shown.

usage: python3 -I check_lessons.py DRAFT [--cap N] [--lesson-cap N]

Prints `chars: N`, then one `line N: reason` per violation; exits 1 when there is any.
Rules (SKILL.md section 3):
  - the whole draft is at most --cap characters (default 16000), and each lesson, from its
    `## ══ LESSON` heading to the next part, at most --lesson-cap (default 5000);
  - outside code fences, no trailing space and no double-width character (emoji, CJK);
  - outside code fences, only ASCII and the allow-listed glyphs;
  - inside ```text fences, no line over 70 columns, and every box row (starting ╭ │ ╰)
    exactly 70 columns, so the right border lines up.
Code fences (any fence with a language other than text) are the source's own characters and
are not checked.
"""
import argparse
import re
import sys
import unicodedata

EXTRA = set("►◄▲▼✔✘≈≠−—·…→↳×")
BOX_START = "╭│╰"
WIDTH = 70


def allowed(ch):
    o = ord(ch)
    return o < 128 or 0x2500 <= o <= 0x259F or 0x2190 <= o <= 0x21FF or ch in EXTRA


def columns(line):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line)


def check(text, cap, lesson_cap):
    problems = []
    kind = None  # None outside a fence, else the fence's info word ("text", "cpp", ...)
    lessons = []  # (start line, [lines])
    for n, line in enumerate(text.split("\n"), 1):
        fence = re.match(r"^(`{3,})\s*(\S*)", line)
        if fence:
            kind = None if kind is not None else (fence.group(2) or "text")
            continue
        if re.match(r"^## ══ LESSON", line):
            lessons.append((n, []))
        elif re.match(r"^(## WORTH|╭─ WORTH|NEXT TIME)", line):
            lessons.append((n, None))
        if lessons and lessons[-1][1] is not None:
            lessons[-1][1].append(line)
        if kind is not None and kind != "text":
            continue
        if line != line.rstrip():
            problems.append((n, "trailing space"))
        for ch in sorted(set(line)):
            if unicodedata.east_asian_width(ch) in "WF":
                problems.append((n, f"double-width character {ch!r}"))
            elif not allowed(ch):
                problems.append((n, f"character outside the allow-list {ch!r} (U+{ord(ch):04X})"))
        if kind == "text":
            width = columns(line)
            if line[:1] and line[0] in BOX_START and width != WIDTH:
                problems.append((n, f"box row is {width} columns, must be {WIDTH}"))
            elif width > WIDTH:
                problems.append((n, f"{width} columns, at most {WIDTH}"))
    if len(text) > cap:
        problems.append((0, f"{len(text)} characters, at most {cap}"))
    for start, body in lessons:
        if body is not None and len("\n".join(body)) > lesson_cap:
            problems.append((start, f"lesson is {len(chr(10).join(body))} characters, about {lesson_cap} or less"))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--cap", type=int, default=16000)
    ap.add_argument("--lesson-cap", type=int, default=5000)
    args = ap.parse_args()
    text = open(args.draft, encoding="utf-8").read()
    problems = check(text, args.cap, args.lesson_cap)
    print(f"chars: {len(text)}")
    for n, why in sorted(problems):
        print(f"line {n}: {why}" if n else why)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
