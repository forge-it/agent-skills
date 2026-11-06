---
name: ask-advisor
description: "Use when the operator invokes /ask-advisor <session>, or tells this session to send its questions to a named advisor session instead of asking them. Never self-select it."
argument-hint: "<advisor session name>"
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.1.1"
---

# Ask the advisor

For the rest of this session, questions go to the advisor session named by the argument, not to
the operator.

Run `ListAgents` first: it prints this session's own name and the running peers. Without an
argument, ask the operator once which of them is the advisor; if the named advisor is not
listed, tell the operator and ask them directly.

Every question you would otherwise put to the operator (with `AskUserQuestion` or in chat) goes
to the advisor over `SendMessage`. Each message gives this session's name as `ListAgents` prints
it, without any ` [ref]` (the advisor uses it as the nag id), the ticket you are working on (key
and title; without a ticket, the repository and branch), the question, the options you see and
your recommendation.

**Operator-level questions block.** A question is operator-level when the decision belongs to
the operator, not the advisor: scope or requirements they have not settled, an approval or gate
that a skill or their instructions reserve for them, a trade-off that is theirs. For those:

1. Tell the advisor in the message that it is operator-level: it must nag the operator with the
   `nag` from `~/.bashrc` until they answer, then stop it and relay the answer here. In a
   Claude Code shell that function is not loaded, so give the advisor the script directly:

   ```
   ~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py start <this session's name> \
     --title "<this session's name>: <the question in a few words>"
   ~/Projects/agent-skills/software-engineering/agent-sync/scripts/nag.py stop <this session's name>
   ```

2. End your turn and wait: the advisor's reply arrives as a cross-session message. Do not go
   ahead on a guess or work around the question. If the operator answers here instead, tell
   the advisor so it stops the nag.
