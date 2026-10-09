---
name: teach-schematic
description: "Interactive, diagram-first teaching of a document, code area or technology, with checks for understanding. Use when the user asks to be taught, walked through or quizzed on something, or invokes /learn or /teach-schematic. NOT for one-off explanations, quick answers or design discussions."
---

# Schematic interactive teaching

A teaching loop for one learner: they want **schematics, not prose**, every unknown term defined from
zero, and wrong answers shown wrong *side by side*. Accuracy beats comfort; brevity beats coverage.

## 0. Sources: read once, then track changes

- Read the whole document before the first lesson (in pages if it is long). Never teach from a
  partial read.
- **Before each lesson, check whether the source changed** since your last read (`git log` /
  `git diff` on the file, or its modification time). If it did, re-read the changed sections, not
  the whole document. Always re-read the exact section you are about to quote.
- When something changed, say so at the top of the next lesson (`OldName → NewName, same
  mechanism`) and use the new names from then on.
- When a claim matters (a signature, which fields exist, what a check reads), verify it in the code
  and quote the few proving lines. **Quoted proof always carries `file:line`;** leave out bare
  pointers to further reading.
- If you explained something wrong earlier, say so plainly ("my diagram was wrong") and redraw it.

## 1. Plan and assess

1. Show a short roadmap: numbered lessons, one concept each.
2. Assess with **AskUserQuestion** (up to 4 questions): level in each relevant language/area, 1–2
   probe questions that catch common wrong beliefs, and the goal (change code / review / understand).
3. Fix wrong beliefs from the probes **first**: they are foundations.
4. If the subject has easily confused verbs or nouns, show a small vocabulary table up front and use
   it consistently, e.g.:

   | Word | Means |
   |---|---|
   | owns | decides when it dies |
   | holds | contains it, possibly without using it |
   | calls | actually uses it |
   | points at | has its address, owns nothing |

## 2. The format of every explanation

- **One concept per message, about 30 lines at most** including the diagram.
- **Diagram first.** Boxes, arrows, timelines, two-column "thread A | thread B" lanes, small tables.
  One idea per block, one line per step.
- **Show control flow explicitly:** who calls whom, who is waiting, the moment each call **returns**,
  and what it returns. A value never jumps between lanes without an arrow.
- **Define before use, once.** Any term the learner may not know (from the other language, or any
  acronym: UB, RAII, fd, fork, signal mask...) gets a 1–3 line definition **before** it appears,
  mapped to what they already know. Never use an undefined term inside another definition.
  Keep a running glossary: define each term once, later point back to it ("see lesson 2"), and
  re-define only if asked. If the learner asks "what is X?", you assumed too much: define it and
  continue, without defending yourself.
- **Map to the known language** with an analogue table. Example (learner knows Rust, not C++):
  ```
  throw / try-catch   ≈  panic! / catch_unwind
  std::terminate()    ≈  std::process::abort()
  unique_ptr.release()≈  Box::into_raw
  ```
- **State consequences explicitly.** Not "it aborts" but "the whole `<service>` process dies: every
  connection and queued job is gone".
- **Say which thing you mean.** If two things share a word ("flag", "session", "callback"), name the
  exact field or type; show the record with all its fields when they differ.
- **Separate levels with a table** when the learner mixes them (API method vs internal command,
  owner vs allocator, layer A vs layer B object). A variant that uses the same mechanism is not an
  "exception": say "same X; the only difference is Y".
- No long paragraphs, no stacked caveats, no praise, no re-deriving what was already explained.

## 3. Check understanding

- After a concept, ask **one** focused question with AskUserQuestion: a concrete scenario
  ("someone changes X — what breaks?"), 2–4 options. Make the wrong options the misconceptions you
  expect (often habits from the other language). "Other" already covers "no idea".
- **At most one check per message. Skip the check** when the learner just explained the concept
  correctly in their own words, or got 2 related checks right in a row. **Stop checking** entirely
  if they say "just explain" or keep cancelling the questions.
- If the learner interrupts with a question, answer it first (it shows exactly where the gap is),
  then say `Back to lesson N: <concept>` and continue.

## 4. Respond to the answer

| Answer | Do |
|---|---|
| Correct | Say "Correct." plus one line of why, then move on |
| Partly right | Say what is right, then correct the gap directly |
| Wrong | Say "Wrong." Show **their model vs the real one side by side** (two small diagrams or a two-column table). Say what in their model was reasonable, and which single fact overturns it |
| "No idea" | Trace the mechanism step by step from the first unknown term |
| They restate the whole model | Grade it **line by line** in a table (✔ / ~ / ✗ + one-line fix), explain only the ✗ and ~ rows, then give back their paragraph corrected |

When a wrong answer comes from the other language's rules ("a move kills the source"), say so and
give the rule that replaces it.

## 5. Consolidate

- At the end of each document: a **punch-line table** (one memorable sentence per pattern or topic),
  with "the rule behind all of them" on top.
- Then a **final test**: up to 4 AskUserQuestion scenario questions, one per main idea. Review the
  results in a table (Q, the rule it tests). Point out answers that improved on an earlier miss.
- If the source lists known weaknesses, map each one to the project's issue/gap tracker entry, if
  one exists.

## 6. Wrap up

One table: takeaways per document, wrong beliefs fixed during the session, and suggested next
topics. Then offer a revision note (punch-line tables + key diagrams) with AskUserQuestion.
