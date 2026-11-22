---
name: ask-advisor
description: "Use when the operator invokes /ask-advisor <session>, or tells this session to send its questions to a named advisor session instead of asking them. Never self-select it."
argument-hint: "<advisor session name>"
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.2.0"
---

# Ask the advisor

For the rest of this session, questions go through the advisor session named by the argument
instead of to the operator.

Run `ListAgents` first: it prints this session's own name and the running peers. Without an
argument, ask the operator once which of them is the advisor; if the named advisor is not
listed, tell the operator and ask them directly.

Every question you would otherwise put to the operator (with `AskUserQuestion` or in chat) goes
to the advisor over `SendMessage`. Each message gives this session's name as `ListAgents` prints
it, without any ` [ref]`, the ticket you are working on (key and title; without a ticket, the
repository and branch), the question, the options you see and your recommendation.

**Sort the question before sending anything.**

- **A standing instruction covers it** (what the operator asked for in this task, the project's
  shared instructions, an answer they already gave for this task): act on it. No message, no
  prompt, no nag. Routine dispatch, progress and a gate those instructions already cover are never
  questions.
- **Technical judgment inside the assigned scope**: the advisor; act on its reply. Where the
  project or the operator designates it technical coordinator, that reply is the coordinator's
  decision, not a recommendation.
- **Reserved or genuinely new**: operator-level, except a permission prompt or denial in this
  session (last paragraph).

**Operator-level questions go on to the operator, once.** A question is operator-level when the
decision belongs to the operator, not the advisor: scope or requirements they have not settled,
an approval or gate that a skill or their instructions reserve for them, a trade-off that is
theirs. That a peer session or a worker asked you does not make it one. Mark it operator-level in
the message, so the advisor nags the operator with the `nag` from `~/.bashrc` until they answer
(its `technical-solution-advisor` skill says how), then relays the answer here. Do not also ask it
here: one question, in one place.

After a question is sent, the work that depends on it waits: the advisor's reply arrives as a
cross-session message. Do not go ahead on a guess or work around the question. If the operator
answers here instead, tell the advisor so it stops the nag, and go on with their answer.

**A permission prompt is answered where it appears.** When the harness is waiting on an action in
this session, or has denied one, no relayed message stands in for the operator's answer to that
prompt. Stop a denied action; do not get it done through another worker, session, worktree or
tool. If the work needs the approval, ask the operator here, once, and tell the advisor which
session holds the prompt: it can point the operator to it, and asks nothing about it itself.
