---
name: ask-advisor
description: "Use when the operator invokes /ask-advisor <session>, or tells this session to send its questions to a named advisor session instead of asking them. Never self-select it."
argument-hint: "<advisor session name>"
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.1.4"
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

**Operator-level questions go on to the operator.** A question is operator-level when the
decision belongs to the operator, not the advisor: scope or requirements they have not settled,
an approval or gate that a skill or their instructions reserve for them, a trade-off that is
theirs. Mark it operator-level in the message, so the advisor nags the operator with the `nag`
from `~/.bashrc` until they answer (its `technical-solution-advisor` skill says how), then
relays the answer here.

Either way, end your turn and wait: the advisor's reply arrives as a cross-session message. Do
not go ahead on a guess or work around the question. If the operator answers here instead, tell
the advisor so it stops the nag, and go on with their answer.
